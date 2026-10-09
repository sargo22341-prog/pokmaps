"""Formes embarquées à part : variantes fixes/animées et normales/chromatiques de chaque forme."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.form_sprites import CASTFORM, DEOXYS, UNOWN, form_sprites_of, validate_form_sprites


def test_unown_variants(assets: Path) -> None:
    validate_form_sprites(assets / "sprites", UNOWN)
    assert len(UNOWN.forms) == 28
    for style in ("", "shiny"):
        for form in UNOWN.forms:
            with Image.open(assets / "sprites/unown" / style / "animated" / f"{form}.webp") as image:
                assert image.is_animated


def test_forms_follow_the_species_of_the_games() -> None:
    assert form_sprites_of(set(range(1, 252))) == (UNOWN,)
    assert form_sprites_of(set(range(1, 387))) == (UNOWN, CASTFORM, DEOXYS)
    # Deoxys : forme Normale dans Rubis et Saphir (sprite de l'espèce), les trois autres dans Émeraude, Rouge Feu
    # et Vert Feuille.
    assert DEOXYS.forms == ("attack", "defense", "speed")


def test_missing_form_fails_validation(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        validate_form_sprites(tmp_path, UNOWN)
