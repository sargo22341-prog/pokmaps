"""Réutilisation exacte des images, invalidation des pixels et corruption visible."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pokemaps_data import maps_render, maps_tiles_gen4
from pokemaps_data.maps_frame_cache_gen4 import FrameCache
from pokemaps_data.maps_raster_gen4 import ONE, RasterMaterial, RasterTexture, RasterVertex
from pokemaps_data.maps_render import DisplayMap, level_count, write_region_tiles, write_tiles
from pokemaps_data.maps_render_cache import RenderCache
from pokemaps_data.maps_render_gen4 import BlockRender
from pokemaps_data.maps_tiles_gen4 import BlockSource, TileJob, render_job
from pokemaps_data.pret_gen4_textures import PALETTE_16, Texture


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
@pytest.mark.parametrize("size", [(256, 256), (321, 281)])
def test_cached_map_is_byte_identical_to_the_direct_encoder(tmp_path: Path, mode: str, size: tuple[int, int]) -> None:
    image = Image.new("RGBA", size, (13, 25, 37, 0)).convert(mode)
    image.putpixel((11, 19), (51, 63, 75) if mode == "RGB" else (51, 63, 75, 255))
    direct, cold, warm = (tmp_path / name for name in ("direct", "cold", "warm"))
    display = DisplayMap("carte", *image.size, level_count(*image.size), image)
    cache = RenderCache.for_tiles(tmp_path / "cache")
    write_tiles(display, direct)
    write_tiles(display, cold, cache)
    write_tiles(display, warm, cache)
    for original in direct.glob("*/*.webp"):
        relative = original.relative_to(direct)
        assert original.read_bytes() == (cold / relative).read_bytes() == (warm / relative).read_bytes()
    image.putpixel((11, 19), (0, 0, 0) if mode == "RGB" else (0, 0, 0, 255))
    write_tiles(display, warm, cache)
    assert (warm / "0/0_0.webp").read_bytes() != (cold / "0/0_0.webp").read_bytes()


def test_map_hit_avoids_encoding_and_does_not_include_obsolete_tiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = RenderCache.for_tiles(tmp_path / "cache")
    image = Image.new("RGBA", (32, 32), "red")
    display = DisplayMap("carte", 32, 32, 1, image)
    output = tmp_path / "first"
    write_tiles(display, output, cache)
    image.paste((0, 0, 0, 0), (0, 0, 32, 32))
    assert write_tiles(display, output, cache) == 0

    def reject_encoder(*_args: object) -> None:
        pytest.fail("Une carte identique ne doit pas être réencodée")

    monkeypatch.setattr(maps_render, "_write_tiles", reject_encoder)
    fresh = tmp_path / "fresh"
    assert write_tiles(display, fresh, cache) == 0
    assert not list(fresh.glob("*/*.webp"))


@pytest.mark.parametrize("origin", [(528, 272), (-16, -32)])
def test_region_cache_preserves_tile_coordinates(tmp_path: Path, origin: tuple[int, int]) -> None:
    image = Image.new("RGBA", (32, 48), "blue")
    cache = RenderCache.for_tiles(tmp_path / "cache")
    direct, cold, warm = (tmp_path / name for name in ("direct", "cold", "warm"))
    expected = write_region_tiles(image, origin, (1024, 1024), direct)
    assert write_region_tiles(image, origin, (1024, 1024), cold, cache) == expected
    assert write_region_tiles(image, origin, (1024, 1024), warm, cache) == expected
    for path in direct.glob("*/*.webp"):
        relative = path.relative_to(direct)
        assert path.read_bytes() == (warm / relative).read_bytes()


def test_corrupt_cache_fails_with_the_file_name(tmp_path: Path) -> None:
    cache = RenderCache(tmp_path)
    cache.write("a" * 64, b"pixels")
    path = tmp_path / "aa" / ("a" * 64)
    path.write_bytes(b"pixels corrompus")
    with pytest.raises(ValueError, match=str(path).replace("\\", "\\\\")):
        cache.read("a" * 64)


def _frame(tmp_path: Path) -> tuple[TileJob, tuple]:
    vertices = tuple(RasterVertex((x * ONE, 0, y * ONE), (0, 0), (31, 0, 0)) for x, y in ((0, 0), (16, 0), (0, 16)))
    triangles = ((vertices, RasterMaterial(None, 31, 3)),)
    source = BlockSource(BlockRender(0, 0, 0), (0, 0), (0, 0, 16, 16))
    job = TileJob(tmp_path / "repo", (), tmp_path / "cold", (0, 0), (32, 32), (0, 0), (source,))
    return job, triangles


def test_frame_hit_avoids_rasterization_and_keeps_the_tiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job, triangles = _frame(tmp_path)
    renderer = SimpleNamespace(
        frames=FrameCache.for_sources(job.root), prepare_block=lambda _: triangles, frame_cache_hits=0
    )
    assert render_job(job, renderer) == 1

    def reject_raster(*_args: object) -> None:
        pytest.fail("Un cadre identique ne doit pas être rasterisé une deuxième fois")

    monkeypatch.setattr(maps_tiles_gen4, "_render_frame", reject_raster)
    warm = replace(job, output=tmp_path / "warm")
    assert render_job(warm, renderer) == 1
    assert renderer.frame_cache_hits == 1
    assert (job.output / "0_0.webp").read_bytes() == (warm.output / "0_0.webp").read_bytes()


@pytest.mark.parametrize("field,value", [("ceiling", ONE), ("origin", (1, 0)), ("size", (16, 16))])
def test_frame_placement_changes_invalidate_the_cache(tmp_path: Path, field: str, value: object) -> None:
    job, triangles = _frame(tmp_path)
    cache = FrameCache.for_sources(job.root)
    prepared = [(job.sources[0], triangles)]
    assert cache.key(job, prepared) != cache.key(replace(job, **{field: value}), prepared)


def test_geometry_and_raster_revision_invalidate_the_cache(tmp_path: Path) -> None:
    job, triangles = _frame(tmp_path)
    cache = FrameCache.for_sources(job.root)
    source = job.sources[0]
    key = cache.key(job, [(source, triangles)])
    vertices, material = triangles[0]
    changed = ((tuple(replace(vertex, color=(0, 0, 31)) for vertex in vertices), material),)
    assert key != cache.key(job, [(source, changed)])
    assert key != replace(cache, revision="autre moteur").key(job, [(source, triangles)])


def test_texture_pixels_and_sampling_invalidate_the_frame(tmp_path: Path) -> None:
    job, triangles = _frame(tmp_path)
    vertices, material = triangles[0]
    source = Texture("motif", 1, 1, PALETTE_16, False, (False, False), (False, False), b"\0")
    texture = RasterTexture(source, ((31, 0, 0, 31),))
    cache = FrameCache.for_sources(job.root)

    def key(value: RasterTexture) -> str:
        changed = ((vertices, replace(material, texture=value)),)
        return cache.key(job, [(job.sources[0], changed)])

    original = key(texture)
    assert original != key(replace(texture, pixels=((0, 0, 31, 31),)))
    assert original != key(replace(texture, source=replace(source, repeat=(True, False))))
    assert original != key(replace(texture, source=replace(source, flip=(False, True))))
