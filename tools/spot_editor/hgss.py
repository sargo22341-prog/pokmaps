"""Adaptateur de l'aperçu HGSS : mêmes contrôles d'édition, sans base Android artificielle."""

import hashlib
from pathlib import Path

from PIL import Image

from pokemaps_data.map_spots import SPOT_KINDS, Point
from pokemaps_data.placement_hgss import FAMILY
from pokemaps_data.preview_placement_hgss import check_placement

from .catalog import EditorMap, EncounterLine, Family, MapMark

_VERSIONS = {"heartgold": "Or HeartGold", "soulsilver": "Argent SoulSilver"}
_METHODS = {
    "walk": "Marche",
    "surf": "Surf",
    "old-rod": "Canne",
    "good-rod": "Super Canne",
    "super-rod": "Méga Canne",
    "headbutt": "Coup d’Boule",
    "rock-smash": "Éclate-Roc",
}


class HgssCatalog:
    def __init__(self, folder: Path) -> None:
        # Les retouches invalides doivent rester ouvrables pour être corrigées dans la liste d'erreurs.
        data = check_placement(folder, validate_spots=False)
        self.records = {r["identifier"]: r for r in data["catalog"]["maps"]}
        self.species = data["catalog"]["species_fr"]
        self.maps_root = folder.parent / "hgss-maps/atlas"
        self.excluded = {(r["map"], r["kind"]) for r in data["coverage"] if r["reason"]}

    def families(self) -> list[Family]:
        return [Family(FAMILY, "Or HeartGold et Argent SoulSilver", (FAMILY,))]

    def maps(self, family: Family) -> list[EditorMap]:
        return sorted((self._map(r) for r in self.records.values()), key=lambda m: m.name)

    def _map(self, record: dict) -> EditorMap:
        return EditorMap(
            FAMILY,
            record["identifier"],
            record["name_fr"],
            FAMILY,
            (record["header"],),
            record["identifier"],
            0,
            0,
            *record["size"],
        )

    def version_map(self, family: Family, identifier: str, version_group: str) -> EditorMap | None:
        record = self.records.get(identifier)
        return self._map(record) if record else None

    def available_groups(self, family: Family, identifier: str) -> tuple[str, ...]:
        return (FAMILY,) if identifier in self.records else ()

    def world_names(self, family: Family) -> dict[str, str]:
        return {"johto": "Johto", "kanto": "Kanto", "special": "Installations et gabarits Safari"}

    def encounters(self, editor_map: EditorMap) -> list[EncounterLine]:
        return [
            EncounterLine(
                _VERSIONS[r["version"]],
                r["method"],
                _METHODS[r["method"]],
                r["species"],
                self.species[str(r["species"])],
                r["minimum"],
                r["maximum"],
                None,
            )
            for r in self.records[editor_map.identifier]["lines"]
        ]

    def generated_spots(self, editor_map: EditorMap) -> dict[str, frozenset[Point]]:
        generated = self.records[editor_map.identifier]["generated"]
        return {
            kind: frozenset()
            if (editor_map.identifier, kind) in self.excluded
            else frozenset(map(tuple, generated.get(kind, [])))
            for kind in SPOT_KINDS
        }

    def marks(self, editor_map: EditorMap) -> list[MapMark]:
        return [MapMark("warp", x, y, None, None, None) for x, y in self.records[editor_map.identifier]["warps"]]

    def image(self, editor_map: EditorMap) -> Image.Image:
        record = self.records[editor_map.identifier]
        path = self.maps_root / record["image"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["image_sha256"]:
            raise ValueError(f"HGSS : image de placement modifiée : {path}")
        with Image.open(path) as source:
            return source.convert("RGBA")

    def kinds(self, family: Family, identifier: str) -> frozenset[str]:
        return frozenset(
            kind for kind in self.records[identifier]["terrain"] if (identifier, kind) not in self.excluded
        )

    def points(self, family: Family, identifier: str, kind: str) -> frozenset[Point]:
        return frozenset(map(tuple, self.records[identifier]["terrain"].get(kind, [])))

    def region(self, family: Family, identifier: str) -> str:
        return self.records[identifier]["scope"]

    def rejected_versions(self, family: Family, identifier: str, kind: str, point: Point) -> tuple[str, ...]:
        return () if point in self.points(family, identifier, kind) else ("Or HeartGold / Argent SoulSilver",)

    def snap(self, family: Family, identifier: str, kind: str, x: float, y: float) -> Point | None:
        points = self.points(family, identifier, kind)
        nearest = min(points, key=lambda p: ((p[0] - x) ** 2 + (p[1] - y) ** 2, p), default=None)
        if nearest is not None and (nearest[0] - x) ** 2 + (nearest[1] - y) ** 2 <= 12**2:
            return nearest
        return None
