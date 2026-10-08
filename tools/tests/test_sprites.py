"""Images embarquées : sprites des Pokémon (normaux et chromatiques) et icônes d'objets."""

import sqlite3
from pathlib import Path

from PIL import Image


def test_sprites(assets: Path, db: sqlite3.Connection) -> None:
    """Un seul style de sprite, normal et chromatique : le sprite fixe est la première image du sprite animé
    (même taille, même pose)."""
    sprites = assets / "sprites"
    assert sorted(path.name for path in (sprites / "pokemon").iterdir()) == ["animated", "shiny", "static"]
    assert sorted(path.name for path in (sprites / "pokemon/shiny").iterdir()) == ["animated", "static"]
    for folder in (sprites / "pokemon", sprites / "pokemon/shiny"):
        for (pokemon_id,) in db.execute("SELECT id FROM pokemon ORDER BY id"):
            with Image.open(folder / "animated" / f"{pokemon_id}.webp") as animated:
                assert (animated.format, animated.is_animated) == ("WEBP", True)
                animated.seek(0)
                first = animated.convert("RGBA")
            with Image.open(folder / "static" / f"{pokemon_id}.webp") as static:
                assert (static.format, getattr(static, "is_animated", False)) == ("WEBP", False)
                assert static.size == first.size
                assert static.convert("RGBA").getchannel("A").tobytes() == first.getchannel("A").tobytes()
    # Le chromatique change les couleurs, pas le dessin.
    with (
        Image.open(sprites / "pokemon/static/6.webp") as normal,
        Image.open(sprites / "pokemon/shiny/static/6.webp") as shiny,
    ):
        assert normal.convert("RGB").tobytes() != shiny.convert("RGB").tobytes()
    missing = [
        identifier
        for identifier, has_sprite in db.execute("SELECT identifier, has_sprite FROM item")
        if has_sprite != (sprites / "items" / f"{identifier}.webp").is_file()
    ]
    assert missing == []
    assert {row[0] for row in db.execute("SELECT identifier FROM item WHERE has_sprite = 0")} == {
        "berserk-gene",
        "flower-mail",
        "eon-mail",
        "surf-mail",
        "liteblue-mail",
        "portrait-mail",
        "lovely-mail",
        "exp-share",
    }


# --- Cartes -----------------------------------------------------------------------
