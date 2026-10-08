"""Toutes les formes de Zarbi ont des variantes fixes/animées et normales/chromatiques."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.unown_sprites import FORMS, validate_unown_sprites


def test_unown_variants(assets: Path) -> None:
    validate_unown_sprites(assets / "sprites")
    assert len(FORMS) == 28
    for style in ("", "shiny"):
        for form in FORMS:
            with Image.open(assets / "sprites/unown" / style / "animated" / f"{form}.webp") as image:
                assert image.is_animated


def test_missing_form_fails_validation(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        validate_unown_sprites(tmp_path)
