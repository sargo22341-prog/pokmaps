"""Invariants du catalogue des Pokémon fixes de Rouge Feu et Vert Feuille."""

import json
from collections import Counter
from pathlib import Path

from .sources import PRET_COMMITS


def validate_remake_fixed(assets: Path) -> None:
    path = assets / "maps/firered-leafgreen/fixed_encounters.json"
    catalog = json.loads(path.read_text("utf-8"))
    if catalog["schema"] != 1 or catalog["repo"] != "pokefirered":
        raise ValueError(f"{path} : format de catalogue fixe invalide")
    if catalog["commit"] != PRET_COMMITS["pokefirered"]:
        raise ValueError(f"{path} : commit source inattendu")
    if set(catalog["versions"]) != {"firered", "leafgreen"}:
        raise ValueError(f"{path} : versions des Pokémon fixes invalides")
    for version, rows in catalog["versions"].items():
        validate_remake_rows(version, rows)


def validate_remake_rows(version: str, rows: list[dict[str, object]]) -> None:
    expected = Counter(
        {
            ("SPECIES_SNORLAX", 30): 2,
            ("SPECIES_ELECTRODE", 34): 2,
            ("SPECIES_ARTICUNO", 50): 1,
            ("SPECIES_ZAPDOS", 50): 1,
            ("SPECIES_MOLTRES", 50): 1,
            ("SPECIES_MEWTWO", 70): 1,
            ("SPECIES_HYPNO", 30): 1,
            ("SPECIES_HO_OH", 70): 1,
            ("SPECIES_LUGIA", 70): 1,
            ("SPECIES_DEOXYS", 30): 1,
        }
    )
    if Counter((row["pokemon"], row["level"]) for row in rows) != expected:
        raise ValueError(f"{version} : espèces, niveaux ou nombres de Pokémon fixes invalides")
    for row in rows:
        event = row["pokemon"] in {"SPECIES_HO_OH", "SPECIES_LUGIA", "SPECIES_DEOXYS"}
        ticket = "ITEM_AURORA_TICKET" if row["pokemon"] == "SPECIES_DEOXYS" else "ITEM_MYSTIC_TICKET"
        if row["event"] != event or row["access_item"] != (ticket if event else None):
            raise ValueError(f"{version}:{row['map']} : accès événementiel invalide")
        if not row["requirements"] or not row["source"] or not str(row["removal_flag"]).startswith("FLAG_"):
            raise ValueError(f"{version}:{row['map']} : provenance ou conditions absentes")
        if not all(isinstance(row[key], int) and row[key] >= 0 for key in ("x", "y", "elevation")):
            raise ValueError(f"{version}:{row['map']} : position invalide")
