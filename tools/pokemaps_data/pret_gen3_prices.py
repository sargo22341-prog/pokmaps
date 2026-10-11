"""Prix des objets dans les sources GBA épinglées, sans prix des jeux modernes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_gen3_source import read_json

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


def item_prices(repo: Gen3PretRepo) -> dict[str, int]:
    rows = _price_rows(repo)
    if not 1 <= len(rows) <= 1024 or len(dict(rows)) != len(rows):
        raise ValueError(f"{repo.root} : prix des objets absents, répétés ou trop nombreux")
    constants = repo.offers[repo.versions[0][0]].scripts.constants
    if unknown := {item for item, _ in rows} - constants.keys():
        raise ValueError(f"{repo.root} : objets tarifés inconnus : {sorted(unknown)}")
    prices = {constants[item]: price for item, price in rows}
    if len(prices) != len(rows) or any(not 0 <= price <= 65535 for price in prices.values()):
        raise ValueError(f"{repo.root} : identifiants ou montants de prix invalides")
    return {name: prices[value] for name, value in constants.items() if name.startswith("ITEM_") and value in prices}


def _price_rows(repo: Gen3PretRepo) -> list[tuple[str, int]]:
    if repo.remake:
        path = repo.root / "src/data/items.json"
        items = read_json(path).get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 1024:
            raise ValueError(f"{path} : liste d’objets absente ou trop grande")
        rows = []
        for item in items:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("itemId"), str)
                or not item["itemId"].startswith("ITEM_")
                or type(item.get("price")) is not int
                or not 0 <= item["price"] <= 65535
            ):
                raise ValueError(f"{path} : prix d’objet invalide : {item}")
            if item["itemId"] != "ITEM_NONE":
                rows.append((item["itemId"], item["price"]))
        return rows
    filename = "items_en.h" if repo.ruby else "items.h"
    text = repo.source_text(f"src/data/{filename}", repo.versions[0][0])
    return [
        (item, int(price))
        for item, price in re.findall(r"\.itemId\s*=\s*(ITEM_\w+),\s*\.price\s*=\s*(\d+)", text)
        if item != "ITEM_NONE"
    ]
