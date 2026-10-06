from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.webp import TRANSPARENT, cached_webp, encode_all

RED = (200, 30, 30, 255)
BLUE = (30, 30, 200, 255)


def _sprite(color: tuple[int, int, int, int], *, hollow: bool = True) -> Image.Image:
    """Image 8 × 8 transparente avec un carré de couleur, évidé en son centre comme le contour d'un sprite."""
    image = Image.new("RGBA", (8, 8), TRANSPARENT)
    image.paste(color, (2, 2, 6, 6))
    if hollow:
        image.paste(TRANSPARENT, (3, 3, 5, 5))
    return image


def _gif(path: Path, frames: list[Image.Image], durations: list[int] | None) -> Path:
    options = {} if durations is None else {"duration": durations}
    frames[0].save(path, save_all=True, append_images=frames[1:], loop=0, disposal=2, **options)
    return path


def _decoded(path: Path) -> list[tuple[bytes, int]]:
    with Image.open(path) as image:
        frames = []
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            frames.append((image.convert("RGBA").tobytes(), image.info.get("duration", 0)))
    return frames


def test_static_image_keeps_its_pixels(tmp_path: Path) -> None:
    source = tmp_path / "icon.png"
    _sprite(RED).save(source)

    webp = encode_all([source])[source]

    with Image.open(webp) as image:
        assert image.format == "WEBP"
    assert _decoded(webp) == [(_sprite(RED).tobytes(), 0)]


def test_animation_keeps_frames_durations_and_transparency(tmp_path: Path) -> None:
    source = _gif(tmp_path / "anim.gif", [_sprite(RED), _sprite(RED), _sprite(BLUE)], [100, 50, 200])

    webp = encode_all([source])[source]

    with Image.open(webp) as image:
        assert (image.format, image.is_animated, image.info["background"]) == ("WEBP", True, TRANSPARENT)
    # Les deux premières images, identiques, n'en font qu'une qui dure aussi longtemps qu'elles deux.
    assert _decoded(webp) == [(_sprite(RED).tobytes(), 150), (_sprite(BLUE).tobytes(), 200)]


def test_animation_losing_its_transparency_is_refused(tmp_path: Path) -> None:
    # Parties visibles toutes opaques : libwebp omet l'alpha et le fond deviendrait noir.
    frames = [_sprite(RED, hollow=False), _sprite(BLUE, hollow=False)]
    source = _gif(tmp_path / "anim.gif", frames, [100, 100])

    with pytest.raises(ValueError, match="différent de son image source"):
        encode_all([source])
    assert [path.name for path in tmp_path.iterdir()] == ["anim.gif"]


def test_animation_without_duration_is_refused(tmp_path: Path) -> None:
    source = _gif(tmp_path / "anim.gif", [_sprite(RED), _sprite(BLUE)], durations=None)

    with pytest.raises(ValueError, match="sans durée"):
        encode_all([source])
    assert not cached_webp(source).exists()


def test_encoded_images_are_reused_from_cache(tmp_path: Path) -> None:
    source = tmp_path / "icon.png"
    _sprite(BLUE).save(source)
    webp = encode_all([source, source])[source]
    encoded_at = webp.stat().st_mtime_ns

    assert encode_all([source]) == {source: webp}
    assert webp.stat().st_mtime_ns == encoded_at
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(["icon.png", webp.name])
