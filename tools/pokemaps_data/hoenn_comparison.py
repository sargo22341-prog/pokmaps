"""Écarts avec PokéAPI : pret garde les caractéristiques propres aux cartouches GBA."""

from .pokeapi import PokeApi


def compare_berries(api: PokeApi, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    items = api.by_id("items")
    berries = {items[int(row["item_id"])]["identifier"]: row for row in api.table("berries")}
    flavors = {
        (int(row["berry_id"]), int(row["contest_type_id"])): int(row["flavor"]) for row in api.table("berry_flavors")
    }
    result = []
    for berry in rows:
        current = berries[str(berry["identifier"])]
        values = {
            "stage_hours": int(current["growth_time"]),
            "max_yield": int(current["max_harvest"]),
            "smoothness": int(current["smoothness"]),
            "flavors": [flavors[int(current["id"]), category] for category in range(1, 6)],
        }
        for key, value in values.items():
            if berry[key] != value:
                result.append({"identifier": berry["identifier"], "field": key, "pret": berry[key], "pokeapi": value})
    return result


def compare_contests(api: PokeApi, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    moves, effects = api.by_id("moves"), api.by_id("contest_effects")
    names = api.names("move_names", "move_id")
    combos: dict[int, list[str]] = {}
    for combo in api.table("contest_combos"):
        combos.setdefault(int(combo["second_move_id"]), []).append(names[int(combo["first_move_id"])])
    result = []
    for move in rows:
        current = moves[int(move["id"])]
        effect = effects[int(current["contest_effect_id"])]
        values = {
            "appeal": int(effect["appeal"]),
            "jam": int(effect["jam"]),
            "previous": sorted(combos.get(int(move["id"]), [])),
        }
        for key, value in values.items():
            actual = sorted(move[key]) if key == "previous" else move[key]
            if actual != value:
                result.append({"id": move["id"], "field": key, "pret": actual, "pokeapi": value})
    return result
