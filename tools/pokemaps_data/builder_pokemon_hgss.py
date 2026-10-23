"""Adaptation des tables natives HGSS aux référentiels communs de la base."""

from pathlib import Path

from .pret_gen4_moves import effect_key
from .pret_gen4_source import c_defines
from .pret_hgss_pokemon import read_hgss_pokemon
from .pret_moves import PretMove


def moves(root: Path) -> list[PretMove]:
    native = read_hgss_pokemon(root)
    names = {
        value: key.removeprefix("MOVE_")
        for key, value in c_defines(root / "include/constants/moves.h", "MOVE_").items()
        if not key.startswith("MOVE_ATTRIBUTE_") and 1 <= value <= 467
    }
    return [
        PretMove(
            names[row["id"]],
            effect_key(row["effect"]),
            row["power"],
            row["pp"],
            chance_percent=row["effect_chance"] if 0 < row["effect_chance"] < 100 else None,
        )
        for row in native.moves
    ]


def forms() -> list[tuple]:
    from .placement_hgss import read_placement_json
    from .sources import PREVIEW_DIR

    catalog = read_placement_json(PREVIEW_DIR / "hgss-pokemon/pokemon.json")
    defaults = {
        351: "castform",
        386: "deoxys-normal",
        412: "burmy-plant",
        413: "wormadam-plant",
        421: "cherrim-overcast",
        422: "shellos-west",
        423: "gastrodon-west",
        479: "rotom",
        487: "giratina-altered",
        492: "shaymin-land",
        493: "arceus-normal",
    }
    return [
        (
            {"heartgold": 15, "soulsilver": 16}[r["version"]],
            int(r["pokemon_id"]),
            r["identifier"],
            r["name_fr"],
            r["sprite_folder"],
            r["sprite_identifier"],
            int(r["identifier"] == defaults[int(r["pokemon_id"])]),
            index,
            *(r["personal"][key] for key in ("hp", "atk", "def", "spatk", "spdef", "speed")),
        )
        for index, r in enumerate(catalog["forms"])
    ]
