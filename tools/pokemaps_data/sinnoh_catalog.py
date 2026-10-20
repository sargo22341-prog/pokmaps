"""Catalogue DS versionné, distinct de la base Room et des règles Hoenn."""

from __future__ import annotations

import json
from pathlib import Path

from .hoenn_catalog import translations
from .pokeapi import PokeApi
from .pret_gen4_source import metang_enum
from .pret_sinnoh_content import CATEGORIES, berries, contest_appeals, contests
from .sinnoh_catalog_extras import content_extras
from .sources import PRET_COMMITS, fetch_pokeapi_csv, fetch_pret
from .validate_sinnoh_content import validate_extras

CATALOG = "sinnoh.json"
_GROUPS = (("diamond-pearl", "pokediamond"), ("platinum", "pokeplatinum"))


def build_sinnoh_catalog(cache: Path, assets: Path) -> None:
    api = PokeApi(fetch_pokeapi_csv(cache))
    roots = {group: fetch_pret(cache, repo) for group, repo in _GROUPS}
    platinum = roots["platinum"]
    ids = metang_enum(platinum / "generated/move_contest_effects.txt")
    descriptions = translations("contest_effects_gen4_fr.csv", "description_fr", 23)
    if set(descriptions) != set(ids) - {"CONTEST_EFFECT_NONE", "CONTEST_EFFECT_MAX"}:
        raise ValueError("Super Concours : traductions des effets incomplètes")
    effects = {ids[key]: value for key, value in descriptions.items()}
    names = api.names("item_names", "item_id")
    items = {row["identifier"]: names[int(row["id"])] for row in api.table("items") if int(row["id"]) in names}
    groups = {}
    for group, repo in _GROUPS:
        root = roots[group]
        appeals = contest_appeals(root)
        moves = contests(root, group == "platinum", ids)
        groups[group] = {
            "commit": PRET_COMMITS[repo],
            "berries": [{**row, "name": items[row["identifier"]]} for row in berries(root, group == "platinum")],
            "moves": [
                {**row, "appeal": appeals[row["effect_id"]], "effect": effects[row["effect_id"]]} for row in moves
            ],
            **content_extras(api, root, platinum, group),
        }
    assets.mkdir(parents=True, exist_ok=True)
    (assets / CATALOG).write_text(
        json.dumps({"schema": 1, "groups": groups}, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validate_sinnoh_catalog(assets)


def validate_sinnoh_catalog(assets: Path) -> None:
    path = assets / CATALOG
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError(f"{path} : catalogue Sinnoh trop volumineux")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["schema"] != 1 or set(data["groups"]) != {group for group, _ in _GROUPS}:
        raise ValueError(f"{path} : schéma ou groupes invalides")
    for group, repo in _GROUPS:
        value = data["groups"][group]
        if value["commit"] != PRET_COMMITS[repo]:
            raise ValueError(f"{path} : {group} : commit invalide")
        _validate_berries(value["berries"], group)
        validate_extras(value, group == "platinum")
        moves = value["moves"]
        if len(moves) != 467 or {row["id"] for row in moves} != set(range(1, 468)):
            raise ValueError(f"{path} : {group} : attaques de concours incomplètes")
        for row in moves:
            if not (
                row["category"] in CATEGORIES
                and 1 <= row["effect_id"] <= 23
                and 0 <= row["appeal"] <= 4
                and row["effect"].strip()
            ):
                raise ValueError(f"{path} : {group} : attaque de concours invalide : {row}")


def _validate_berries(rows: list[dict], group: str) -> None:
    if len(rows) != 64 or len({row["identifier"] for row in rows}) != 64:
        raise ValueError(f"sinnoh.json : {group} : 64 baies uniques attendues")
    for row in rows:
        if not (
            row["identifier"].endswith("-berry")
            and row["name"].strip()
            and 1 <= row["stage_hours"] <= 24
            and row["min_yield"] == 2
            and 5 <= row["max_yield"] <= 15
            and 1 <= row["drain_rate"] <= 100
            and 0 <= row["smoothness"] <= 255
            and len(row["flavors"]) == 5
            and all(0 <= number <= 40 for number in row["flavors"])
        ):
            raise ValueError(f"sinnoh.json : {group} : baie invalide : {row}")
