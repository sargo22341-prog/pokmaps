"""Décor ajouté par les moteurs DS : état initial des plateformes et engrenages des arènes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

from .maps_geometry_gen4 import Transform
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_maps_dp import _labelled_bytes
from .pret_gen4_source import ByteReader, read_text

_PT_GYM = "src/overlay008/gym_features.c"
_DP_GYM = "arm9/overlays/06/asm/overlay_06.s"
# Quarts de tour des engrenages, puis angles de l'horloge à 7 h 25 ; coefficients fx12 de FX_SinIdx/CosIdx.
_SIN_COS = {
    0: (0, 4096),
    16384: (4096, 0),
    32768: (0, -4096),
    49152: (-4096, 0),
    60049: (-2057, 3542),
    54595: (-3551, 2041),
}


@dataclass(frozen=True)
class DynamicProp:
    header: int
    model: int
    position: tuple[int, int, int]
    rotation: tuple[int, int, int]
    evidence: str


def prop_rotation(angles: tuple[int, int, int]) -> Transform:
    result = Transform()
    for axis, angle in enumerate(angles):
        if angle not in _SIN_COS:
            raise ValueError(f"rotation de décor DS non relue : {angles}")
        sine, cosine = _SIN_COS[angle]
        matrices = (
            (4096, 0, 0, 0, cosine, sine, 0, -sine, cosine),
            (cosine, 0, -sine, 0, 4096, 0, sine, 0, cosine),
            (cosine, sine, 0, -sine, cosine, 0, 0, 0, 4096),
        )
        result = result.then(Transform(matrices[axis]))
    return result


class DynamicProps:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo

    @cached_property
    def placements(self) -> tuple[DynamicProp, ...]:
        return _platinum(self.repo) if self.repo.platinum else _diamond(self.repo)

    @cached_property
    def by_block(self) -> dict[tuple[int, int], tuple[DynamicProp, ...]]:
        result: dict[tuple[int, int], list[DynamicProp]] = {}
        for prop in self.placements:
            header = self.repo.headers[prop.header]
            matrix = self.repo.matrices[header.matrix]
            x, _, z = prop.position
            column, row = x // 512, z // 512
            if not 0 <= column < matrix.width or not 0 <= row < matrix.height:
                raise ValueError(f"{prop.evidence} : décor hors de la matrice : {prop}")
            block = matrix.blocks[row][column]
            if block == 0xFFFF or prop.model not in self.repo.prop_sets[self.repo.areas[header.area].prop_set]:
                raise ValueError(f"{prop.evidence} : bloc ou modèle de décor absent : {prop}")
            local = DynamicProp(
                prop.header, prop.model, (x % 512, prop.position[1], z % 512), prop.rotation, prop.evidence
            )
            result.setdefault((block, header.area), []).append(local)
        return {key: tuple(props) for key, props in result.items()}


def _table(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\[[^\]]+\]\s*=\s*\{{(.*?)\n\}};", text, re.DOTALL)
    if match is None:
        raise ValueError(f"{_PT_GYM} : table de décor absente : {name}")
    return match[1]


def _vector(text: str, name: str) -> tuple[int, int, int]:
    match = re.search(rf"\.{name}\s*=\s*\{{\s*\.x = (\d+), \.y = (\d+), \.z = (\d+)\s*\}}", text)
    if match is None:
        raise ValueError(f"position de décor absente : {name}")
    return tuple(map(int, match.groups()))


def _placed(
    header: int,
    model: int,
    point: tuple[int, int, int],
    rotation: tuple[int, int, int],
    evidence: str,
    centered: bool = True,
) -> DynamicProp:
    position = (point[0] * 16 + (8 if centered else 0), point[1] * 16, point[2] * 16 + (8 if centered else 0))
    return DynamicProp(header, model, position, rotation, evidence)


def _platinum(repo: Gen4PretRepo) -> tuple[DynamicProp, ...]:
    text = read_text(repo.root / _PT_GYM)
    models = {
        name.replace(".", "_"): index
        for name, index in repo.names.order("res/field/props/models/map_prop_models.order").items()
    }
    result = []
    for level, name in enumerate(("second", "third", "fourth"), 1):
        model = models[f"canalave_gym_{name}_floor_nsbmd"]
        result.append(_placed(35, model, (16, level * 10, 16), (0, 0, 0), _PT_GYM, False))
    rows = re.findall(
        r"\{\s*\.modelID = (\w+),(.*?)\.startInPositionB = (TRUE|FALSE),\s*\}",
        _table(text, "sCanalavePlatformPaths"),
        re.DOTALL,
    )
    if len(rows) != 24:
        raise ValueError(f"{_PT_GYM} : les 24 plateformes de Joliberges sont attendues")
    for name, body, state in rows:
        point = _vector(body, "positionB" if state == "TRUE" else "positionA")
        result.append(_placed(35, models[name], point, (0, 0, 0), _PT_GYM))
    for room, count in enumerate((3, 6, 13), 1):
        body = _table(text, f"sSunyshoreRoom{room}Gears")
        gears = re.findall(
            r"\.modelID = (\w+),\s*\.x = (\d+),\s*\.y = (\d+),\s*\.z = (\d+),"
            r"\s*\.initialRotation = (\d+),\s*\.turnsClockwise = (TRUE|FALSE),"
            r"\s*\.isVertical = (TRUE|FALSE)",
            body,
        )
        if len(gears) != count:
            raise ValueError(f"{_PT_GYM} : engrenages incomplets dans la salle {room}")
        for name, x, y, z, angle, _, vertical in gears:
            result.append(
                _gear(153 + room, models[name], (int(x), int(y), int(z)), int(angle), vertical == "TRUE", _PT_GYM)
            )
    result.append(_placed(122, models["pastoria_gym_water_floor_nsbmd"], (16, 2, 16), (0, 0, 0), _PT_GYM, False))
    for model, y, angle in (("hour", 12, 60049), ("minute", 13, 54595)):
        position = (11 * 16 + 8, y, 13 * 16 + 8)
        result.append(
            DynamicProp(67, models[f"eterna_gym_model_clock_{model}_hand_nsbmd"], position, (0, angle, 0), _PT_GYM)
        )
    return tuple(result) + _pt_transport(repo, models)


def _gear(
    header: int, model: int, point: tuple[int, int, int], angle: int, vertical: bool, evidence: str
) -> DynamicProp:
    rotation = (angle * 16384, 0, 0) if vertical else (0, angle * 16384, 0)
    prop = _placed(header, model, point, rotation, evidence)
    position = (prop.position[0], prop.position[1] + (8 if vertical else 0), prop.position[2])
    return DynamicProp(header, model, position, rotation, evidence)


def _diamond(repo: Gen4PretRepo) -> tuple[DynamicProp, ...]:
    path = repo.root / _DP_GYM
    text = read_text(path)
    table = text.split("ov06_0224FA80:", 1)[1].split("ov06_0224FC00:", 1)[0]
    raw = bytes(
        int(value, 16) for row in re.findall(r"^\s*\.byte ([^\n]+)", table, re.MULTILINE) for value in row.split(",")
    )
    if len(raw) != 24 * 16:
        raise ValueError(f"{path} : table des plateformes de taille incorrecte")
    reader = ByteReader(raw, str(path))
    center = ByteReader(_labelled_bytes(path, "ov06_0224F78C"), str(path)).unpack("3i", 0)
    if center != (256 * 4096, 0, 256 * 4096) or "lsl r2, r2, #2" not in text:
        raise ValueError(f"{path} : position centrale de Joliberges modifiée")
    result = [_placed(35, 299 + level, (16, level * 10, 16), (0, 0, 0), _DP_GYM, False) for level in range(1, 4)]
    for offset in range(0, len(raw), 16):
        values = reader.unpack("I3B3B2BH2x", offset)
        point = values[4:7] if values[9] else values[1:4]
        result.append(_placed(35, values[0], point, (0, 0, 0), _DP_GYM))
    for room, (label, count) in enumerate((("ov06_0224F7BC", 3), ("ov06_0224F7D4", 6), ("ov06_0224F978", 13)), 1):
        data = _labelled_bytes(path, label)
        if len(data) != count * 8:
            raise ValueError(f"{path} : engrenages incomplets : {label}")
        gears = ByteReader(data, str(path))
        for offset in range(0, len(data), 8):
            model, x, y, z, flags = gears.unpack("I4B", offset)
            result.append(_gear(153 + room, model, (x, y, z), flags & 3, bool(flags & 8), _DP_GYM))
    if "mov r2, #0xf2" not in text:
        raise ValueError(f"{path} : modèle d'eau de Verchamps absent")
    result.append(_placed(122, 242, (16, 2, 16), (0, 0, 0), _DP_GYM, False))
    return tuple(result) + _dp_other(repo, text)


def _pt_transport(repo: Gen4PretRepo, models: dict[str, int]) -> tuple[DynamicProp, ...]:
    lift_path = "src/platform_lift.c"
    lift = read_text(repo.root / lift_path)
    if "(16 * 19 + 8)" not in lift or "(16 * (MAP_TILES_COUNT_Z + 12) + 8)" not in lift:
        raise ValueError(f"{lift_path} : position de la plateforme de l'Île de Fer modifiée")
    tram_path = "src/overlay006/great_marsh_tram.c"
    tram = read_text(repo.root / tram_path)
    if "position.x = FX32_CONST(1056);" not in tram or "(32 * 3 + 12)" not in tram:
        raise ValueError(f"{tram_path} : position du tramway modifiée")
    return (
        DynamicProp(293, models["iron_island_platform_lift_nsbmd"], (312, 16, 712), (0, 0, 0), lift_path),
        DynamicProp(509, models["great_marsh_train_nsbmd"], (1056, 16, 1728), (0, 0, 0), tram_path),
    )


def _dp_other(repo: Gen4PretRepo, text: str) -> tuple[DynamicProp, ...]:
    path = repo.root / _DP_GYM
    table = text.split("ov06_0224F8B8:", 1)[1].split("ov06_0224F918:", 1)[0]
    data = bytes(
        int(value, 16) for row in re.findall(r"^\s*\.byte ([^\n]+)", table, re.MULTILINE) for value in row.split(",")
    )
    init_path = repo.root / "arm9/asm/unk_02064CA8.s"
    flags = _labelled_bytes(init_path, "UNK_020F7E48")
    if len(data) != 12 * 8 or len(flags) != 12:
        raise ValueError(f"{path} : cloisons de Voilaroc incomplètes")
    reader = ByteReader(data, str(path))
    result = []
    for index in range(12):
        model, z, x_a, x_b, _ = reader.unpack("I4B", index * 8)
        x = x_b if flags[index] else x_a
        result.append(DynamicProp(133, model, (x * 16 + 32, -16, z * 16 + 8), (0, 0, 0), _DP_GYM))
    center = ByteReader(_labelled_bytes(path, "ov06_0224F7A4"), str(path)).unpack("3i", 0)
    position = tuple(value // 4096 for value in center)
    for header in (88, 91):
        result.append(DynamicProp(header, 258, (position[0], 160, position[2]), (0, 0, 0), _DP_GYM))
    lift_path = repo.root / "arm9/asm/unk_020647A4.s"
    lift = ByteReader(_labelled_bytes(lift_path, "UNK_020F7D64"), str(lift_path)).unpack("3i", 0)
    result.append(
        DynamicProp(293, 258, (lift[0] // 4096, 16, lift[2] // 4096), (0, 0, 0), str(lift_path.relative_to(repo.root)))
    )
    if "mov r1, #0x42" not in text or "mov r0, #0x1b" not in text or "0x000001DB" not in text:
        raise ValueError(f"{path} : initialisation du tramway modifiée")
    result.append(DynamicProp(509, 475, (1056, 16, 1728), (0, 0, 0), _DP_GYM))
    return tuple(result)
