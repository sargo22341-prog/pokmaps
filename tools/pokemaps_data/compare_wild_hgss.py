"""Comparaison HGSS par banque, méthode et configuration ; les écarts gardent les deux distributions."""

from collections import defaultdict

from .encounters_hgss import Distribution, Period, Slot, signature
from .pokeapi import PokeApi


def _api_tables(api: PokeApi) -> dict[tuple[int, int, str], list[tuple[Slot, frozenset[str]]]]:
    slots = api.by_id("encounter_slots")
    methods = api.by_id("encounter_methods")
    conditions = api.by_id("encounter_condition_values")
    pokemon = api.by_id("pokemon")
    values: dict[int, set[str]] = defaultdict(set)
    for row in api.table("encounter_condition_value_map"):
        values[int(row["encounter_id"])].add(conditions[int(row["encounter_condition_value_id"])]["identifier"])
    tables = defaultdict(list)
    for row in api.table("encounters"):
        version = int(row["version_id"])
        if version not in (15, 16):
            continue
        slot = slots[int(row["encounter_slot_id"])]
        method = methods[int(slot["encounter_method_id"])]["identifier"]
        species = int(pokemon[int(row["pokemon_id"])]["species_id"])
        entry = Slot(species, int(row["min_level"]), int(row["max_level"]), int(slot["rarity"]))
        tables[(version, int(row["location_area_id"]), method)].append((entry, frozenset(values[int(row["id"])])))
    return tables


def area_bindings(api: PokeApi) -> dict[int, int]:
    """PokéAPI HGSS numérote les banques natives à partir de 1, et non de 0."""
    used = {int(r["location_area_id"]) for r in api.table("encounters") if int(r["version_id"]) in (15, 16)}
    result = {}
    for row in api.table("location_areas"):
        index = int(row["game_index"])
        if int(row["id"]) not in used or not 1 <= index <= 142:
            continue
        if index - 1 in result:
            raise ValueError(f"HGSS : correspondance PokéAPI ambiguë pour la banque {index - 1}")
        result[index - 1] = int(row["id"])
    return result


def compare_tables(tables: tuple[Distribution, ...], api: PokeApi) -> dict:
    old = _api_tables(api)
    bindings = area_bindings(api)
    differences = []
    equal = 0
    compared = set()
    for table in tables:
        config = table.configuration
        period = {Period.MORNING: "morning", Period.DAY: "day", Period.NIGHT: "night"}[config.period]
        selected = {
            f"time-{period}",
            f"radio-{config.radio.value}",
            "swarm-yes" if config.swarm else "swarm-no",
            "bug-catching-contest-no",
        }
        key = (15 if table.version == "heartgold" else 16, bindings.get(table.bank, -1), table.method)
        compared.add(key)
        rows = old.get(key, [])
        previous = tuple(slot for slot, conditions in rows if conditions <= selected)
        current = signature(table.slots)
        if signature(previous) == current:
            equal += 1
            continue
        differences.append(
            {
                "version": table.version,
                "bank": table.bank,
                "area": key[1],
                "method": table.method,
                "period": config.period.value,
                "radio": config.radio.value,
                "swarm": config.swarm,
                "category": _category(table, rows, previous),
                "pokeapi": signature(previous),
                "engine": current,
            }
        )
    source_only = [
        {
            "version": key[0],
            "area": key[1],
            "method": key[2],
            "category": "table_absente_moteur",
            "native_headers": [386, 387],
            "engine": [],
            "pokeapi": [
                {"slot": (s.species, s.minimum, s.maximum, s.chance), "conditions": sorted(c)} for s, c in old[key]
            ],
        }
        for key in sorted(old.keys() - compared)
        if key[1] == 349
    ]
    return {
        "equal": equal,
        "differences": differences,
        "area_bindings": bindings,
        "source_only": source_only,
        "not_compared": _excluded_tables({k for k in old.keys() - compared if k[1] != 349}, api),
    }


def _excluded_tables(keys: set[tuple[int, int, str]], api: PokeApi) -> list[dict]:
    areas = api.by_id("location_areas")
    locations = api.by_id("locations")
    result = []
    for version, area, method in sorted(keys):
        location = locations[int(areas[area]["location_id"])]["identifier"]
        if method == "headbutt":
            reason = "Tables communes, rares et particulières séparées dans le moteur ; catégorie absente de PokéAPI"
        elif method in ("walk", "surf", "old-rod", "good-rod", "super-rod"):
            if "safari-zone" not in location:
                raise ValueError(f"HGSS : table PokéAPI ordinaire non comparée : {version}/{area}/{method}")
            reason = "Parc Safari : configurations et blocs réservés au lot 4C"
        else:
            reason = "Obtention particulière réservée au lot 4D"
        result.append({"version": version, "area": area, "method": method, "location": location, "reason_fr": reason})
    return result


def _category(table: Distribution, rows: list, previous: tuple[Slot, ...]) -> str:
    if not rows:
        return "table_absente_pokeapi"
    if not previous:
        return "configuration_absente_pokeapi"
    if sum(slot.chance for slot in previous) != 100:
        return "distribution_pokeapi_non_normalisee"
    species_old = {slot.species for slot in previous}
    species_new = {slot.species for slot in table.slots}
    if species_old != species_new:
        return "especes_ou_remplacements"
    levels_old = {(s.species, s.minimum, s.maximum) for s in previous}
    levels_new = {(s.species, s.minimum, s.maximum) for s in table.slots}
    if levels_old != levels_new:
        return "niveaux"
    return "probabilites"
