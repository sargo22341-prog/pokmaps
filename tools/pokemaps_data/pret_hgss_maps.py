"""Lecture minimale HGSS, sans chemin de repli vers les autres jeux DS ou Game Boy."""

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .pret_gen4_land import LandBlock
from .pret_gen4_map_models import Gen4Matrix
from .pret_gen4_source import c_defines, read_json, read_text
from .pret_hgss_binary import read_archive, read_land, read_matrix

PROOF_MAPS = ("NEW_BARK", "NEW_BARK_ELMS_LAB_1F", "ROUTE_29", "NEW_BARK_ELMS_LAB_2F", "ROUTE_47")
_BLOCK = re.compile(r"\[(MAP_\w+)\] = \{(.*?)\},", re.DOTALL)
_FIELD = re.compile(r"\.(\w+)\s*=\s*([^,\n]+),")
_HEADER_FIELDS = frozenset(
    (
        "wildEncounterBank",
        "areaDataBank",
        "moveModelBank",
        "worldMapX",
        "worldMapY",
        "matrixId",
        "scriptsBank",
        "scriptHeaderBank",
        "msgBank",
        "dayMusicId",
        "nightMusicId",
        "eventsBank",
        "mapsec",
        "areaIcon",
        "momCallIntroParam",
        "regionNo",
        "weather",
        "mapType",
        "cameraType",
        "followMode",
        "battleBg",
        "bikeAllowed",
        "runningAllowed_Unused",
        "escapeRopeAllowed",
        "flyAllowed",
        "outgoingCalls",
        "incomingCalls",
        "radioSignal",
    )
)


@dataclass(frozen=True)
class HgssHeader:
    index: int
    constant: str
    area: int
    matrix: int
    events: int
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HgssWarp:
    x: int
    z: int
    y: int
    destination: int
    anchor: int


@dataclass(frozen=True)
class HgssActor:
    identity: str
    sprite: str
    x: int
    z: int
    y: int
    direction: int
    script: str
    flag: str


@dataclass(frozen=True)
class HgssEvents:
    source: str
    warps: tuple[HgssWarp, ...]
    actors: tuple[HgssActor, ...]


def _archive_index(value: str, prefix: str, where: str) -> int:
    match = re.fullmatch(rf"{prefix}_(\d+)(?:_\w+)?_bin", value)
    if match is None:
        raise ValueError(f"{where} : référence d'archive HGSS inconnue : {value}")
    return int(match[1])


def _read_headers(root: Path) -> dict[int, HgssHeader]:
    path = root / "src/data/map_headers.h"
    constants = c_defines(root / "include/constants/maps.h", "MAP_")
    result = {}
    for constant, body in _BLOCK.findall(read_text(path)):
        pairs = _FIELD.findall(body)
        fields = dict(pairs)
        if len(pairs) != len(_HEADER_FIELDS) or set(fields) != _HEADER_FIELDS or constant not in constants:
            raise ValueError(f"{path} {constant} : champs d'en-tête HGSS inattendus")
        header = HgssHeader(
            constants[constant],
            constant,
            int(fields["areaDataBank"]),
            _archive_index(fields["matrixId"], "NARC_map_matrix_map_matrix", constant),
            _archive_index(fields["eventsBank"], "NARC_zone_event", constant),
            tuple(pairs),
        )
        if header.index in result:
            raise ValueError(f"{path} : en-tête répété : {constant}")
        result[header.index] = header
    if len(result) != 540:
        raise ValueError(f"{path} : 540 en-têtes HGSS attendus, {len(result)} lus")
    return result


class HgssMapRepo:
    def __init__(self, root: Path, version: str) -> None:
        if version not in ("heartgold", "soulsilver"):
            raise ValueError(f"{root} : version HGSS invalide : {version}")
        self.root = root
        self.version = version

    @cached_property
    def headers(self) -> dict[int, HgssHeader]:
        return _read_headers(self.root)

    @cached_property
    def terrain(self) -> tuple[bytes, ...]:
        return read_archive(self.root / "files/a/0/6/5")

    def matrix(self, header: HgssHeader) -> Gen4Matrix:
        folder = self.root / "files/fielddata/mapmatrix/map_matrix"
        paths = tuple(folder.glob(f"map_matrix_{header.matrix:04d}*.bin"))
        if len(paths) != 1:
            raise ValueError(f"{folder} : matrice {header.matrix} absente ou ambiguë")
        from .pret_gen4_source import read_binary

        return read_matrix(read_binary(paths[0]), header.matrix, str(paths[0]))

    def blocks(self, header: HgssHeader) -> tuple[tuple[int, int, int, int], ...]:
        matrix = self.matrix(header)
        selected = tuple(
            (x, z, block, matrix.altitudes[z][x] if matrix.altitudes else 0)
            for z, row in enumerate(matrix.blocks)
            for x, block in enumerate(row)
            if block != 0xFFFF and (matrix.headers is None or matrix.headers[z][x] == header.index)
        )
        if not selected or any(block >= len(self.terrain) for _, _, block, _ in selected):
            raise ValueError(f"{header.constant} : terrain absent ou hors de l'archive HGSS")
        return selected

    def land(self, index: int) -> LandBlock:
        if not 0 <= index < len(self.terrain):
            raise ValueError(f"{self.version} : bloc HGSS inconnu : {index}")
        return read_land(self.terrain[index], f"files/a/0/6/5 membre {index}")

    def events(self, header: HgssHeader) -> HgssEvents:
        folder = self.root / "files/fielddata/eventdata/zone_event"
        paths = tuple(folder.glob(f"{header.events:03d}_*.json"))
        if len(paths) != 1:
            raise ValueError(f"{folder} : événements {header.events} absents ou ambigus")
        data = read_json(paths[0])
        if "header" not in data or set(data) - {"header", "bgs", "objects", "warps", "coords"}:
            raise ValueError(f"{paths[0]} : sections d'événements HGSS inattendues")
        names = {h.constant: h.index for h in self.headers.values()}
        warps = tuple(_warp(row, names, str(paths[0])) for row in data.get("warps", []))
        actors = tuple(_actor(row, str(paths[0])) for row in data.get("objects", []))
        return HgssEvents(paths[0].relative_to(self.root).as_posix(), warps, actors)


def _warp(row: dict, names: dict[str, int], where: str) -> HgssWarp:
    if set(row) != {"x", "z", "y", "header", "anchor"} or row["header"] not in names:
        raise ValueError(f"{where} : passage HGSS invalide : {row}")
    if any(type(row[key]) is not int or not 0 <= row[key] <= 65535 for key in ("x", "z", "y", "anchor")):
        raise ValueError(f"{where} : coordonnées de passage HGSS invalides : {row}")
    return HgssWarp(row["x"], row["z"], row["y"], names[row["header"]], row["anchor"])


def _actor(row: dict, where: str) -> HgssActor:
    expected = {
        "id",
        "spriteId",
        "movement",
        "type",
        "eventFlag",
        "scriptId",
        "facingDirection",
        "param0",
        "param1",
        "param2",
        "xRange",
        "yRange",
        "x",
        "z",
        "y",
    }
    if set(row) != expected or any(type(row[key]) is not int for key in ("x", "z", "y", "facingDirection")):
        raise ValueError(f"{where} : acteur HGSS invalide : {row}")
    if not 0 <= row["facingDirection"] <= 3 or not all(
        isinstance(row[key], str) for key in ("id", "spriteId", "eventFlag")
    ):
        raise ValueError(f"{where} : identité ou direction d'acteur HGSS invalide : {row}")
    return HgssActor(
        row["id"],
        row["spriteId"],
        row["x"],
        row["z"],
        row["y"],
        row["facingDirection"],
        str(row["scriptId"]),
        row["eventFlag"],
    )
