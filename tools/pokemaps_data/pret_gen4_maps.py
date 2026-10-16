"""Lieux de Platine : en-têtes, matrices, zones, objets posés, éclairages et caméras, lus dans les sources lisibles.

Les noms des JSON et des en-têtes sont convertis en valeurs du moteur comme le fait la construction du dépôt
(tools/jsoncnv, listes *.order et énumérations metang de generated/) ; un nom inconnu arrête la lecture.
"""

from __future__ import annotations

import re
from fractions import Fraction
from functools import cached_property
from pathlib import Path

from .pret_gen4_map_models import (
    EMPTY_BLOCK,
    CameraSettings,
    Gen4Area,
    Gen4Header,
    Gen4Matrix,
    Light,
    LightingPeriod,
)
from .pret_gen4_source import c_defines, c_enum, metang_enum, read_json, read_json_list, read_text

_HEADER_BLOCK = re.compile(r"\[(MAP_HEADER_\w+)\] = \{(.*?)\n    \},", re.DOTALL)
_HEADER_FIELD = re.compile(r"\.(\w+) = ([^,\n]+),")
_HEADER_FIELDS = frozenset(
    {
        "areaDataArchiveID",
        "preloadedMapObjectsArchiveID",
        "mapMatrixID",
        "scriptsArchiveID",
        "initScriptsArchiveID",
        "msgArchiveID",
        "dayMusicID",
        "nightMusicID",
        "wildEncountersArchiveID",
        "eventsArchiveID",
        "mapLabelTextID",
        "mapLabelWindowID",
        "weather",
        "cameraType",
        "mapType",
        "battleBG",
        "isBikeAllowed",
        "isRunningAllowed",
        "isEscapeRopeAllowed",
        "isFlyAllowed",
    }
)
_CAMERA_BLOCK = re.compile(r"\[(CAMERA_TYPE_\w+)\] = \{(.*?)\n    \},", re.DOTALL)


class PlatinumNames:
    """Énumérations et listes d'archives de Platine, lues une fois chacune."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def generated(self, name: str) -> dict[str, int]:
        return metang_enum(self.root / f"generated/{name}.txt")

    def order(self, relative: str) -> dict[str, int]:
        names = [line.strip() for line in read_text(self.root / relative).splitlines() if line.strip()]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.root / relative} : archive répétée")
        return {name: index for index, name in enumerate(names)}

    @cached_property
    def map_headers(self) -> dict[str, int]:
        return self.generated("map_headers")

    @cached_property
    def vars_flags(self) -> dict[str, int]:
        return self.generated("vars_flags")

    @cached_property
    def trainers(self) -> dict[str, int]:
        return self.generated("trainers")

    @cached_property
    def maps(self) -> dict[str, int]:
        return self.generated("maps")

    @cached_property
    def archives(self) -> dict[str, dict[str, int]]:
        return {
            "area": self.order("res/field/area_data/area_data.order"),
            "matrix": self.order("res/field/matrices/map_matrices.order"),
            "scripts": self.order("res/field/scripts/scripts.order"),
            "events": self.order("res/field/events/zone_event.order"),
            "encounters": self.order("res/field/encounters/encounters.order"),
            "prop_set": self.order("res/field/props/model_sets/prop_model_sets.order"),
            "texture_set": self.order("res/field/maps/texture_sets/map_texture_sets.order"),
            "lighting": self.order("res/field/lighting/lighting_sets.order"),
        }


def lookup(table: dict[str, int], name: str, where: str) -> int:
    if name not in table:
        raise ValueError(f"{where} : constante inconnue : {name}")
    return table[name]


def read_headers(root: Path, names: PlatinumNames) -> dict[int, Gen4Header]:
    path = root / "include/data/map_headers.h"
    enums = {
        "mapType": c_enum(path, "MapType"),
        "cameraType": c_enum(root / "include/constants/camera_types.h", "CameraType"),
        "weather": c_defines(root / "include/constants/overworld_weather.h", "OVERWORLD_WEATHER_"),
        "battleBG": names.generated("battle_backgrounds"),
        "msgArchiveID": names.generated("text_banks"),
        "mapLabelWindowID": c_enum(path, "MapLabelWindowID"),
    }
    headers = {}
    for constant, body in _HEADER_BLOCK.findall(read_text(path)):
        fields = dict(_HEADER_FIELD.findall(body))
        if set(fields) != _HEADER_FIELDS:
            raise ValueError(f"{path} {constant} : champs inattendus : {sorted(set(fields) ^ _HEADER_FIELDS)}")
        header = _header(names, enums, lookup(names.map_headers, constant, str(path)), constant, fields)
        headers[header.index] = header
    if len(headers) != len(names.map_headers) - 3:
        raise ValueError(f"{path} : {len(headers)} en-têtes pour {len(names.map_headers)} identifiants")
    return headers


def _header(
    names: PlatinumNames, enums: dict[str, dict[str, int]], index: int, constant: str, fields: dict[str, str]
) -> Gen4Header:
    where = f"map_headers.h {constant}"
    archives = names.archives

    def enum(field: str) -> int:
        return lookup(enums[field], fields[field], where)

    def flag(field: str) -> bool:
        return {"TRUE": True, "FALSE": False}[fields[field]] if fields[field] in {"TRUE", "FALSE"} else _bad(where)

    lookup(enums["mapLabelWindowID"], fields["mapLabelWindowID"], where)
    encounters = fields["wildEncountersArchiveID"]
    return Gen4Header(
        index=index,
        constant=constant,
        area=lookup(archives["area"], fields["areaDataArchiveID"], where),
        move_models=int(fields["preloadedMapObjectsArchiveID"], 0),
        matrix=lookup(archives["matrix"], fields["mapMatrixID"], where),
        scripts=lookup(archives["scripts"], fields["scriptsArchiveID"], where),
        init_scripts=lookup(archives["scripts"], fields["initScriptsArchiveID"], where),
        texts=enum("msgArchiveID"),
        day_music=fields["dayMusicID"].removesuffix("_sseq"),
        night_music=fields["nightMusicID"].removesuffix("_sseq"),
        encounters=()
        if encounters == "ENCOUNTERS_NONE"
        else (("platinum", lookup(archives["encounters"], encounters, where)),),
        events=lookup(archives["events"], fields["eventsArchiveID"], where),
        location=fields["mapLabelTextID"].removeprefix("LocationNames_Text_"),
        weather=enum("weather"),
        camera=enum("cameraType"),
        map_type=enum("mapType"),
        battle_background=enum("battleBG"),
        bike=flag("isBikeAllowed"),
        running=flag("isRunningAllowed"),
        escape_rope=flag("isEscapeRopeAllowed"),
        fly=flag("isFlyAllowed"),
    )


def _bad(where: str) -> bool:
    raise ValueError(f"{where} : booléen TRUE ou FALSE attendu")


def read_matrices(root: Path, names: PlatinumNames) -> dict[int, Gen4Matrix]:
    matrices = {}
    for name, index in names.archives["matrix"].items():
        path = root / f"res/field/matrices/{name}.json"
        data = read_json(path)
        if set(data) != {"name", "headers", "altitudes", "maps"}:
            raise ValueError(f"{path} : clés de matrice inattendues")
        blocks = tuple(tuple(_block(names, value, path) for value in row) for row in data["maps"])
        headers = tuple(tuple(lookup(names.map_headers, h, str(path)) for h in row) for row in data["headers"])
        altitudes = tuple(tuple(_altitude(value, path) for value in row) for row in data["altitudes"])
        matrices[index] = Gen4Matrix(index, data["name"], blocks, headers or None, altitudes or None)
    return matrices


def _block(names: PlatinumNames, value: str, path: Path) -> int:
    block = lookup(names.maps, value, str(path))
    if block != EMPTY_BLOCK and not value.startswith("MAP_"):
        raise ValueError(f"{path} : bloc inattendu : {value}")
    return block


def _altitude(value: object, path: Path) -> int:
    if not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise ValueError(f"{path} : altitude invalide : {value}")
    return value


def read_areas(root: Path, names: PlatinumNames) -> dict[int, Gen4Area]:
    areas = {}
    archives = names.archives
    for name, index in archives["area"].items():
        path = root / f"res/field/area_data/{name}.json"
        data = read_json(path)
        if set(data) != {"mapPropSet", "mapTextureSet", "lightingSet", "dummy"} or not 0 <= data["dummy"] <= 0xFFFF:
            raise ValueError(f"{path} : zone inattendue")
        areas[index] = Gen4Area(
            index,
            lookup(archives["prop_set"], data["mapPropSet"], str(path)),
            lookup(archives["texture_set"], data["mapTextureSet"], str(path)),
            data["dummy"],
            lookup(archives["lighting"], data["lightingSet"], str(path)),
        )
    return areas


def read_lighting(root: Path, names: PlatinumNames) -> dict[int, tuple[LightingPeriod, ...]]:
    return {
        index: tuple(_period(entry, root / f"res/field/lighting/{name}.json") for entry in _lighting_list(root, name))
        for name, index in names.archives["lighting"].items()
    }


def _lighting_list(root: Path, name: str) -> list:
    entries = read_json_list(root / f"res/field/lighting/{name}.json")
    ends = [entry.get("endTime") for entry in entries]
    if not entries or ends != sorted(set(ends)) or ends[-1] > 43_200:
        raise ValueError(f"{name} : heures de fin d'éclairage invalides : {ends}")
    return entries


def _period(entry: dict, path: Path) -> LightingPeriod:
    keys = {"endTime", "lights", "diffuseColor", "ambientColor", "specularColor", "emissionColor"}
    if set(entry) != keys or len(entry["lights"]) != 4:
        raise ValueError(f"{path} : éclairage inattendu : {sorted(entry)}")

    def color(value: dict) -> tuple[int, int, int]:
        rgb = (value["red"], value["green"], value["blue"])
        if not all(isinstance(c, int) and 0 <= c <= 31 for c in rgb):
            raise ValueError(f"{path} : couleur invalide : {value}")
        return rgb

    def fx16(value: float) -> int:
        # Les directions sont écrites en flottants exacts de pas 1/4096.
        fixed = round(value * 4096)
        if fixed / 4096 != value:
            raise ValueError(f"{path} : direction non représentable en fx16 : {value}")
        return fixed

    lights = tuple(
        Light(light["enabled"], color(light["color"]), tuple(fx16(light["direction"][k]) for k in "xyz"))
        for light in entry["lights"]
    )
    return LightingPeriod(
        entry["endTime"],
        lights,
        color(entry["diffuseColor"]),
        color(entry["ambientColor"]),
        color(entry["specularColor"]),
        color(entry["emissionColor"]),
    )


def read_cameras(root: Path) -> tuple[CameraSettings, ...]:
    path = root / "src/overlay005/field_camera.c"
    types = c_enum(root / "include/constants/camera_types.h", "CameraType")
    cameras: dict[int, CameraSettings] = {}
    for name, body in _CAMERA_BLOCK.findall(read_text(path)):
        cameras[lookup(types, name, str(path))] = _camera(body, f"{path} {name}")
    if sorted(cameras) != list(range(len(types))):
        raise ValueError(f"{path} : types de caméra incomplets")
    return tuple(cameras[index] for index in range(len(types)))


def _camera(body: str, where: str) -> CameraSettings:
    def match(pattern: str) -> str:
        found = re.search(pattern, body)
        if found is None:
            raise ValueError(f"{where} : réglage absent : {pattern}")
        return found.group(1)

    # include/camera.h : CAMERA_DEFAULT_NEAR_CLIP = FX32_ONE * 150, CAMERA_DEFAULT_FAR_CLIP = FX32_ONE * 900.
    defaults = {"CAMERA_DEFAULT_NEAR_CLIP": 150, "CAMERA_DEFAULT_FAR_CLIP": 900}

    def clip(field: str) -> int:
        value = match(rf"\.{field} = (\w+(?: \* \d+)?)")
        if value in defaults:
            return defaults[value] * 4096
        if not value.startswith("FX32_ONE * "):
            raise ValueError(f"{where} : plan de coupe non pris en charge : {value}")
        return int(value.removeprefix("FX32_ONE * ")) * 4096

    return CameraSettings(
        distance=fx32_const(match(r"\.distance = FX32_CONST\(([\d.]+)\)")),
        angle_x=-deg_to_index(match(r"\.cameraAngle = \{ -F32_DEG_TO_IDX\(([\d.]+)\), 0, 0 \}")) & 0xFFFF,
        projection={"PERSPECTIVE": 0, "ORTHOGRAPHIC": 1}[match(r"\.projection = CAMERA_PROJECTION_(\w+)")],
        vertical_fov=deg_to_index(match(r"\.verticalFov = F32_DEG_TO_IDX\(([\d.]+)\)")),
        near=clip("nearPlaneDist"),
        far=clip("farPlaneDist"),
    )


def fx32_const(value: str) -> int:
    """FX32_CONST du Nitro SDK : valeur × 4096 arrondie au plus proche (les sources n'ont que des positifs)."""
    return int(Fraction(value) * 4096 + Fraction(1, 2))


def deg_to_index(value: str) -> int:
    """F32_DEG_TO_IDX : degrés en fx32, puis indice de cercle de 65 536 pas (tronqué)."""
    return fx32_const(value) * 65536 // (360 * 4096)


def read_prop_sets(root: Path, names: PlatinumNames) -> dict[int, tuple[int, ...]]:
    """Jeux d'objets posés : indices des modèles dans map_prop_models.order (nommés « fichier_nsbmd »)."""
    models = {
        name.replace(".", "_"): index
        for name, index in names.order("res/field/props/models/map_prop_models.order").items()
    }
    sets = {}
    for name, index in names.archives["prop_set"].items():
        path = root / f"res/field/props/model_sets/{name}.json"
        data = read_json(path)
        if set(data) != {"mapPropModels"}:
            raise ValueError(f"{path} : jeu d'objets inattendu")
        sets[index] = tuple(lookup(models, model, str(path)) for model in data["mapPropModels"])
    return sets
