"""Prototype de rendu HGSS : ressources natives, projection oblique et pose de face d'un acteur."""

import math
import re
from functools import cached_property
from pathlib import Path

from PIL import Image

from .maps_raster_gen4 import RasterCanvas
from .maps_render_gen4 import RasterTriangle, model_triangles
from .maps_sprites_gen4 import read_nitro_frame
from .pret_gen4_land import FX_ONE
from .pret_gen4_map_models import LightingPeriod
from .pret_gen4_maps_dp import read_light_file
from .pret_gen4_nitro import NitroFile, read_nsbmd
from .pret_gen4_source import ByteReader, c_defines, read_text
from .pret_gen4_textures import NitroTextures, read_nsbtx
from .pret_hgss_binary import read_archive
from .pret_hgss_maps import HgssHeader, HgssMapRepo


def camera_cotangent(root: Path, header: HgssHeader) -> int:
    path = root / "asm/overlay_01_021EABA8.s"
    body = read_text(path).split("ov01_02206478:", 1)[1]
    values = bytes(
        int(value, 16)
        for row in body.splitlines()
        if row.strip().startswith(".byte")
        for value in re.findall(r"0x([0-9A-Fa-f]{2})", row)
    )
    camera = int(dict(header.fields)["cameraType"])
    reader = ByteReader(values, str(path))
    angle = reader.u16(36 * camera + 4)
    if not 49152 < angle < 65536:
        raise ValueError(f"{header.constant} : angle de caméra HGSS non pris en charge : {angle}")
    return round(FX_ONE / math.tan((65536 - angle) * 2 * math.pi / 65536))


class HgssRenderer:
    def __init__(self, repo: HgssMapRepo) -> None:
        self.repo = repo
        self._archives: dict[str, tuple[bytes, ...]] = {}
        self._texture_sets: dict[tuple[str, int], NitroTextures] = {}
        self._props: dict[tuple[str, int], NitroFile] = {}

    def _archive(self, name: str) -> tuple[bytes, ...]:
        if name not in self._archives:
            if len(self._archives) >= 8:
                raise ValueError("Prototype HGSS : plus de huit archives de rendu")
            self._archives[name] = read_archive(self.repo.root / "files" / name)
        return self._archives[name]

    def _area(self, header: HgssHeader) -> tuple[int, int, int, int, int]:
        data = self._archive("a/0/4/2")[header.area]
        reader = ByteReader(data, f"zone HGSS {header.area}")
        if len(data) != 8:
            raise ValueError(f"{reader.where} : huit octets attendus")
        return reader.unpack("3H2B", 0)

    def _lighting(self, header: HgssHeader) -> LightingPeriod:
        kind = self._area(header)[4]
        # AreaDataManager_GetAreaLightArchiveID, puis ov01_02206450 : ordre HGSS propre.
        names = {0: "area01light.txt", 1: "area00light.txt", 2: "dun20_01light.txt"}
        if kind not in names:
            raise ValueError(f"{header.constant} : éclairage HGSS non qualifié : {kind}")
        periods = read_light_file(self.repo.root / "files/data" / names[kind])
        return next(period for period in periods if period.end_time >= 25200)

    def _textures(self, archive: str, index: int) -> NitroTextures:
        key = archive, index
        if key not in self._texture_sets:
            if len(self._texture_sets) >= 16:
                raise ValueError("Prototype HGSS : plus de seize jeux de textures")
            self._texture_sets[key] = read_nsbtx(self._archive(archive)[index], f"{archive} membre {index}")
        return self._texture_sets[key]

    def _prop(self, archive: str, index: int) -> NitroFile:
        key = archive, index
        if key not in self._props:
            if len(self._props) >= 128:
                raise ValueError("Prototype HGSS : plus de 128 modèles de décor")
            self._props[key] = read_nsbmd(self._archive(archive)[index], f"{archive} membre {index}")
        return self._props[key]

    def triangles(self, header: HgssHeader, block: int, altitude: int) -> tuple[RasterTriangle, ...]:
        prop_set, texture_set, _, outdoor, _ = self._area(header)
        table = ByteReader(self._archive("a/0/4/3")[prop_set], f"jeu d'objets HGSS {prop_set}")
        count = table.u16(0)
        if len(table.data) != 2 + count * 2:
            raise ValueError(f"{table.where} : nombre de modèles incohérent")
        models = table.unpack(f"{count}H", 2)
        terrain = self.repo.land(block)
        origin = (256 * FX_ONE, altitude * 8 * FX_ONE, 256 * FX_ONE)
        scale = (FX_ONE,) * 3
        light = self._lighting(header)
        textures = (self._textures("a/0/4/4", texture_set), self._textures("a/0/7/0", prop_set))
        result = list(model_triangles(read_nsbmd(terrain.model, f"bloc HGSS {block}"), textures, origin, scale, light))
        for prop in terrain.props:
            model = prop.model if prop.model in models else 0
            position = tuple(a + b for a, b in zip(origin, prop.position, strict=True))
            archive = "a/0/4/0" if outdoor else "a/1/4/8"
            result.extend(model_triangles(self._prop(archive, model), textures[::-1], position, prop.scale, light))
        return tuple(result)

    def render(self, header: HgssHeader, ceiling: int | None = None) -> tuple[Image.Image, tuple[int, int]]:
        blocks = self.repo.blocks(header)
        min_x, min_z = min(b[0] for b in blocks), min(b[1] for b in blocks)
        width = (max(b[0] for b in blocks) - min_x + 1) * 512
        height = (max(b[1] for b in blocks) - min_z + 1) * 512
        origin = (min_x * 512 - 128, min_z * 512 - 256)
        canvas = RasterCanvas(origin, (width + 256, height + 512), camera_cotangent(self.repo.root, header), ceiling)
        prepared = [(x, z, self.triangles(header, block, altitude)) for x, z, block, altitude in blocks]
        for translucent in (False, True):
            for x, z, triangles in prepared:
                for vertices, material in triangles:
                    if (material.alpha < 31) == translucent:
                        canvas.triangle(vertices, material, (x * 512, z * 512))
        return canvas.image(), origin

    @cached_property
    def sprite_models(self) -> dict[str, int]:
        source = read_text(self.repo.root / "asm/overlay_01_sprite_data.s")
        names = c_defines(self.repo.root / "include/constants/mmodel.h", "MMODEL_")
        pairs = re.findall(r"\.short (SPRITE_\w+), (MMODEL_\w+),", source)
        return {sprite: names[model] for sprite, model in pairs if model in names}

    def actor_image(self, sprite: str) -> tuple[Image.Image, str]:
        if sprite not in self.sprite_models:
            raise ValueError(f"HGSS : sprite non qualifié : {sprite}")
        relative = f"files/data/mmodel/mmodel/mmodel_{self.sprite_models[sprite]:08d}.NSBTX"
        return read_nitro_frame(self.repo.root / relative), relative
