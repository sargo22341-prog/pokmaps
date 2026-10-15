"""Descriptions éditoriales des objets absents des textes français PokéAPI."""

import csv

from .sources import DATA_DIR


def read_item_descriptions(ids: dict[str, int]) -> dict[int, str]:
    descriptions: dict[int, str] = {}
    with (DATA_DIR / "item_descriptions.csv").open(encoding="utf-8", newline="") as source:
        for line, row in enumerate(csv.DictReader(source), 2):
            identifier, text = row["identifier"], row["description_fr"].strip()
            if identifier not in ids or ids[identifier] in descriptions or not text:
                raise ValueError(f"item_descriptions.csv:{line} : objet inconnu, répété ou description vide : {row}")
            descriptions[ids[identifier]] = text
    return descriptions
