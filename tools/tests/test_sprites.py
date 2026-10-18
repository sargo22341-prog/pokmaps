"""Images embarquées : sprites des Pokémon (normaux et chromatiques) et icônes d'objets."""

import csv
import json
import sqlite3
from pathlib import Path

from PIL import Image

from pokemaps_data.sources import pokesprite
from pokemaps_data.sprites import icons_by_identifier

from .conftest import CACHE

# Objets de la 3e génération sans numéro de 8e génération dans pokesprite (docs/generations/generation-3.md, phase 0).
GEN3_UNLINKED_ITEMS = (
    "exp-share",
    "vs-seeker",
    *(f"{name}-mail" for name in ("orange", "harbor", "glitter", "mech", "wood", "wave", "bead", "shadow")),
    *(f"{name}-mail" for name in ("tropic", "dream", "fab", "retro")),
    "devon-goods",
    "pokeblock-case",
    *(f"rm-{room}-key" for room in (1, 2, 4, 6)),
    "bike-voucher",
    "fame-checker",
    "berry-pouch",
    "teachy-tv",
    "tri-pass",
    "rainbow-pass",
    "mysticticket",
    "auroraticket",
    "powder-jar",
    "ruby",
    "sapphire",
    "magma-emblem",
    "old-sea-map",
)


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


def test_item_icons_match_their_declared_availability(assets: Path, db: sqlite3.Connection) -> None:
    sprites = assets / "sprites"
    missing = [
        identifier
        for identifier, has_sprite in db.execute("SELECT identifier, has_sprite FROM item")
        if has_sprite != (sprites / "items" / f"{identifier}.webp").is_file()
    ]
    assert missing == []
    with (Path(__file__).parents[1] / "data/extra_items.csv").open(encoding="utf-8", newline="") as source:
        merchandise = {row["identifier"] for row in csv.DictReader(source) if row["identifier"].startswith("sinnoh-")}
    assert len(merchandise) == 61
    assert {row[0] for row in db.execute("SELECT identifier FROM item WHERE has_sprite = 0")} == merchandise | {
        "berserk-gene",
        "coin",
        "oaks-parcel",
        "flower-mail",
        "eon-mail",
        "surf-mail",
        "liteblue-mail",
        "portrait-mail",
        "lovely-mail",
    }


def test_icons_are_found_by_identifier_when_unambiguous() -> None:
    item_map = {"item_0001": "ball/master", "item_0233": "hold-item/metal-coat"}
    unlinked = {"key-item/devon-goods": {}, "evo-item/metal-coat": {}}
    assert icons_by_identifier(item_map, unlinked) == {
        "master": "items/ball/master.png",
        "devon-goods": "items/key-item/devon-goods.png",
    }


def test_every_unlinked_item_of_the_third_generation_has_an_icon(source_cache_ready: None) -> None:
    data = [
        json.loads(pokesprite(CACHE, f"data/{name}.json")[1].read_text("utf-8"))
        for name in ("item-map", "item-unlinked")
    ]
    icons = icons_by_identifier(*data)
    assert len(GEN3_UNLINKED_ITEMS) == 33
    assert {item: icons.get(item) for item in GEN3_UNLINKED_ITEMS if item not in icons} == {}
    assert icons["orange-mail"] == "items/mail/orange-mail.png"


# --- Cartes -----------------------------------------------------------------------
