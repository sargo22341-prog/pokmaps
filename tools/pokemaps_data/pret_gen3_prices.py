"""Prix des objets dans les sources GBA épinglées, sans prix des jeux modernes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


def item_prices(repo: Gen3PretRepo) -> dict[str, int]:
    filename = "items_en.h" if repo.ruby else "items.h"
    text = repo.source_text(f"src/data/{filename}", repo.versions[0][0])
    rows = [
        (item, price)
        for item, price in re.findall(r"\.itemId\s*=\s*(ITEM_\w+),\s*\.price\s*=\s*(\d+)", text)
        if item != "ITEM_NONE"
    ]
    if not 1 <= len(rows) <= 1024 or len(dict(rows)) != len(rows):
        raise ValueError(f"{repo.root} : prix des objets absents, répétés ou trop nombreux")
    constants = repo.offers[repo.versions[0][0]].scripts.constants
    prices = {constants[item]: int(price) for item, price in rows}
    if len(prices) != len(rows) or any(not 0 <= price <= 65535 for price in prices.values()):
        raise ValueError(f"{repo.root} : identifiants ou montants de prix invalides")
    return {name: prices[value] for name, value in constants.items() if name.startswith("ITEM_") and value in prices}
