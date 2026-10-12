"""Catalogue hors ligne des baies, concours et décorations des seuls jeux Hoenn."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .builder_moves import MOVE_ALIASES
from .hoenn_comparison import compare_berries, compare_contests
from .pokeapi import PokeApi
from .pret_hoenn_content import berry_rows, decorations
from .pret_hoenn_contests import ContestMove, contest_effects, contest_moves
from .sources import DATA_DIR, PRET_COMMITS, fetch_pokeapi_csv, fetch_pret

_GROUPS = (("ruby-sapphire", "pokeruby"), ("emerald", "pokeemerald"))
CATALOG = "hoenn.json"


def translations(filename: str, column: str, count: int) -> dict[str, str]:
    with (DATA_DIR / filename).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["identifier"]: row[column] for row in rows}
    invalid = any(not value.strip() or "?" in value for value in result.values())
    if len(rows) != count or len(result) != count or invalid:
        raise ValueError(f"{filename} : {count} traductions uniques et non vides attendues")
    return result


def build_hoenn_catalog(cache: Path, assets: Path) -> None:
    api = PokeApi(fetch_pokeapi_csv(cache))
    names = {
        row["identifier"]: api.names("item_names", "item_id")[int(row["id"])]
        for row in api.table("items")
        if int(row["id"]) in api.names("item_names", "item_id")
    }
    move_names = api.names("move_names", "move_id")
    move_ids = {row["identifier"].replace("-", ""): int(row["id"]) for row in api.table("moves")}
    decoration_names = translations("decorations_fr.csv", "name_fr", 120)
    descriptions = translations("contest_effects_fr.csv", "description_fr", 48)
    payload = {"schema": 1, "groups": {}}
    for group, repo in _GROUPS:
        root = fetch_pret(cache, repo)
        moves = contest_moves(root)
        effects = contest_effects(root)
        starters = {row.starter.removeprefix("COMBO_STARTER_"): row.move for row in moves if row.starter != "0"}
        value = {
            "commit": PRET_COMMITS[repo],
            "berries": berry_rows(root, names),
            "moves": [_move_row(row, effects, descriptions, starters, move_ids, move_names) for row in moves],
            "decorations": [{**asdict(row), "name": decoration_names[row.identifier]} for row in decorations(root)],
            "sources": _decoration_sources(assets / "maps" / group),
        }
        value["comparison"] = compare_berries(api, value["berries"]) + compare_contests(api, value["moves"])
        payload["groups"][group] = value
    path = assets / CATALOG
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    validate_hoenn_catalog(assets)


def _move_row(
    row: ContestMove,
    effects: dict[str, tuple[int, int]],
    descriptions: dict[str, str],
    starters: dict[str, str],
    ids: dict[str, int],
    names: dict[int, str],
) -> dict[str, object]:
    appeal, jam = effects[row.effect]
    return {
        "id": _move_id(row.move, ids),
        "category": row.category.removeprefix("CONTEST_CATEGORY_"),
        "appeal": appeal,
        "jam": jam,
        "effect": descriptions[row.effect],
        "previous": [names[_move_id(starters[name], ids)] for name in row.previous],
    }


def _move_id(name: str, ids: dict[str, int]) -> int:
    identifier = name.lower().replace("_", "-")
    return ids[MOVE_ALIASES.get(identifier, identifier).replace("-", "")]


def _decoration_sources(directory: Path) -> list[dict]:
    path = directory / "characters.json"
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError(f"{path} : catalogue de personnages trop volumineux")
    characters = json.loads(path.read_text(encoding="utf-8"))["characters"]
    if len(characters) > 5000:
        raise ValueError(f"{path} : trop de personnages")
    result = []
    for character in characters:
        for offer in character["result"]["offers"]:
            if offer["kind"] not in {"sale_decoration", "gift_decoration"}:
                continue
            result.append(
                {
                    "identifier": offer["item"],
                    "version": character["version"],
                    "map": character["map_const"].removeprefix("MAP_").lower().replace("_", "-"),
                    "kind": offer["kind"],
                    "price": offer["price"],
                    "currency": offer["currency"] or "money",
                    "paths": offer["paths"],
                }
            )
    return result


def validate_hoenn_catalog(assets: Path) -> None:
    path = assets / CATALOG
    if path.stat().st_size > 512 * 1024:
        raise ValueError("hoenn.json : catalogue trop volumineux")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["schema"] != 1 or set(data["groups"]) != {group for group, _ in _GROUPS}:
        raise ValueError("hoenn.json : schéma ou groupes invalides")
    for group, repo in _GROUPS:
        value = data["groups"][group]
        if value["commit"] != PRET_COMMITS[repo]:
            raise ValueError(f"hoenn.json : {group} : commit invalide")
        for key, identity, count in (
            ("berries", "identifier", 43),
            ("moves", "id", 354),
            ("decorations", "identifier", 120),
        ):
            rows = value[key]
            if len(rows) != count or len({row[identity] for row in rows}) != count:
                raise ValueError(f"hoenn.json : {group} : {key} incomplet ou répété")
        for berry in value["berries"]:
            if not (
                1 <= berry["stage_hours"] <= 24
                and 1 <= berry["min_yield"] <= berry["max_yield"] <= 15
                and len(berry["flavors"]) == 5
                and all(0 <= number <= 40 for number in berry["flavors"])
            ):
                raise ValueError(f"hoenn.json : {group} : baie invalide : {berry}")
        for move in value["moves"]:
            if move["category"] not in {"COOL", "BEAUTY", "CUTE", "SMART", "TOUGH"} or not move["effect"].strip():
                raise ValueError(f"hoenn.json : {group} : concours invalide : {move}")
        ids = {row["identifier"] for row in value["decorations"]}
        if not value["sources"] or any(row["identifier"] not in ids for row in value["sources"]):
            raise ValueError(f"hoenn.json : {group} : source de décoration invalide")
