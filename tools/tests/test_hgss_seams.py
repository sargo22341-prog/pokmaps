"""Les décors traversant deux lieux partagent le même tampon de profondeur."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data import maps_seams_hgss
from pokemaps_data.maps_raster_gen4 import RasterMaterial, RasterVertex
from pokemaps_data.maps_seams_hgss import overlapping_tiles, render_seams
from pokemaps_data.validate_johto_hgss import validate_world_tiles


def _records(root: Path) -> list[dict]:
    for index in range(2):
        Image.new("RGBA", (256, 256), "green").save(root / f"{index}.png")
    return [
        dict(header=i, plan="johto-exterieurs", origin_pixels=(0, 0), size=(256, 256), image=f"{i}.png")
        for i in range(2)
    ]


def test_only_visible_intersections_need_common_depth(tmp_path: Path) -> None:
    records = _records(tmp_path)
    parts = [dict(offset=(0, 0)), dict(offset=(128, 0))]
    assert overlapping_tiles(tmp_path, records, parts) == {(0, 0)}
    Image.new("RGBA", (256, 256)).save(tmp_path / "1.png")
    assert overlapping_tiles(tmp_path, records, parts) == set()


class _Repo:
    root = Path("fixture")

    def __init__(self) -> None:
        self.headers = {0: 0, 1: 1}

    def blocks(self, header: int) -> tuple:
        return ((0, 0, header, 0),)


class _Renderer:
    repo = _Repo()

    def triangles(self, header: int, block: int, altitude: int) -> tuple:
        height = 16 if header == 0 else 0
        color = (31, 0, 0) if header == 0 else (0, 0, 31)
        vertices = tuple(
            RasterVertex((x * 4096, height * 4096, (z + height) * 4096), (0, 0), color)
            for x, z in ((0, 0), (256, 0), (0, 256))
        )
        return ((vertices, RasterMaterial(None, 31, 3)),)


def test_neighboring_ground_does_not_cover_roof_and_order_is_irrelevant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(maps_seams_hgss, "camera_cotangent", lambda root, header: 4096)
    records = _records(tmp_path)
    for order in (records, records[::-1]):
        render_seams(tmp_path, order, [dict(offset=(0, 0))] * 2, _Renderer(), tmp_path)
        with Image.open(tmp_path / "0_0.webp") as tile:
            assert tile.convert("RGBA").getpixel((20, 20)) == (255, 0, 0, 255)


@pytest.mark.parametrize("name,size", [("0_0.webp", (255, 256)), ("0_1.webp", (256, 256))])
def test_world_validation_rejects_invalid_seam_tiles(tmp_path: Path, name: str, size: tuple[int, int]) -> None:
    (tmp_path / "0").mkdir()
    Image.new("RGBA", size).save(tmp_path / "0" / name, "WEBP", lossless=True)
    with pytest.raises(ValueError, match="tuile de raccord HGSS"):
        validate_world_tiles(tmp_path, dict(level_count=1, size=(256, 256)))
