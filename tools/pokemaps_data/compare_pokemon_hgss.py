"""Comparaisons PokéAPI/HGSS : les valeurs exportées restent celles des tables natives."""

from collections import defaultdict

from .pokeapi import PokeApi, value_at
from .pret_hgss_pokemon import HgssPokemon


def compare_pokemon(data: HgssPokemon, api: PokeApi) -> dict:
    _compare_identities(data, api)
    ranks = {
        int(r["species_id"]): int(r["pokedex_number"])
        for r in api.table("pokemon_dex_numbers")
        if r["pokedex_id"] == "7"
    }
    if ranks != {i: rank for i, rank in enumerate(data.regional) if rank}:
        raise ValueError("HGSS : régional natif différent de PokéAPI")
    machines = {
        int(r["machine_number"]) - (8 if int(r["machine_number"]) > 100 else 0): int(r["move_id"])
        for r in api.table("machines")
        if r["version_group_id"] == "10"
    }
    if machines != dict(enumerate(data.machines, 1)):
        raise ValueError("HGSS : CT/CS différentes de PokéAPI")
    expected: dict[int, set[tuple[int, int, int]]] = defaultdict(set)
    for row in api.table("pokemon_moves"):
        pokemon = int(row["pokemon_id"])
        if row["version_group_id"] == "10" and pokemon <= 493:
            expected[pokemon].add((int(row["pokemon_move_method_id"]), int(row["level"]), int(row["move_id"])))
    move_ids = {r["identifier"].replace("-", "_").upper(): int(r["id"]) for r in api.table("moves")}
    tutors = {r["mon"].removeprefix("SPECIES_"): r["moves"] for r in data.tutors}
    differences = []
    tutor_ids = _tutor_ids(data, move_ids)
    for index, row in enumerate(data.personal[1:494], 1):
        native = {(1, level, move) for level, move in data.level_moves[index]}
        native |= {(4, 0, data.machines[n - 1]) for n in row["tms"]}
        native |= {(4, 0, data.machines[91 + n]) for n in row["hms"]}
        native |= {(3, 0, move_ids[m.removeprefix("TUTOR_")]) for m in tutors[row["species"]]}
        selected = {r for r in expected[index] if r[0] in (1, 4) or (r[0] == 3 and r[2] in tutor_ids)}
        if native != selected:
            differences.append(
                dict(species=index, native_only=sorted(native - selected), pokeapi_only=sorted(selected - native))
            )
    return {
        "regional": 256,
        "national": 493,
        "machines": 100,
        "learnset_differences": differences,
        "stat_differences": _compare_stats(data, api),
        "profile_differences": _compare_profiles(data, api),
    }


def _compare_identities(data: HgssPokemon, api: PokeApi) -> None:
    versions = [(r["id"], r["identifier"]) for r in api.table("versions") if r["version_group_id"] == "10"]
    if versions != [("15", "heartgold"), ("16", "soulsilver")]:
        raise ValueError("HGSS : identités des cartouches différentes de PokéAPI")
    species = api.by_id("pokemon_species")
    for i, row in enumerate(data.personal[1:494], 1):
        if _identifier(row["species"]) != _identifier(species[i]["identifier"]):
            raise ValueError(f"HGSS : espèce native {i} différente de PokéAPI")
    native = {
        (_identifier(row["baseSpecies"]), _identifier(e["target"])) for row in data.evolutions for e in row["evos"]
    }
    expected = {
        (_identifier(species[int(row["evolves_from_species_id"])]["identifier"]), _identifier(row["identifier"]))
        for i, row in species.items()
        if i <= 493 and row["evolves_from_species_id"]
    }
    if native != expected:
        raise ValueError(f"HGSS : chaînes d'évolution différentes de PokéAPI : {native ^ expected}")


def _identifier(value: str) -> str:
    return value.removeprefix("SPECIES_").lower().replace("_", "").replace("-", "")


def _tutor_ids(data: HgssPokemon, move_ids: dict[str, int]) -> set[int]:
    return {move_ids[m.removeprefix("TUTOR_")] for row in data.tutors for m in row["moves"]}


def _compare_stats(data: HgssPokemon, api: PokeApi) -> list[dict]:
    current = {(int(r["pokemon_id"]), int(r["stat_id"])): int(r["base_stat"]) for r in api.table("pokemon_stats")}
    past: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for row in api.table("pokemon_stats_past"):
        past[int(row["pokemon_id"]), int(row["stat_id"])].append((int(row["generation_id"]), int(row["base_stat"])))
    differences = []
    for index, row in enumerate(data.personal[1:494], 1):
        for stat, key in enumerate(("hp", "atk", "def", "spatk", "spdef", "speed"), 1):
            expected = value_at(past[index, stat], 4, current[index, stat])
            if row[key] != expected:
                differences.append(dict(species=index, stat=key, native=row[key], pokeapi=expected))
    return differences


def _historical_slots(api: PokeApi, table: str, column: str) -> dict[int, set[int]]:
    current: dict[int, dict[int, int | None]] = defaultdict(dict)
    for row in api.table(table):
        if row.get("is_hidden", "0") == "0":
            current[int(row["pokemon_id"])][int(row["slot"])] = int(row[column])
    past: dict[int, dict[int, list[tuple[int, int | None]]]] = defaultdict(lambda: defaultdict(list))
    for row in api.table(table + "_past"):
        if row.get("is_hidden", "0") == "0":
            past[int(row["pokemon_id"])][int(row["slot"])].append(
                (int(row["generation_id"]), int(row[column]) if row[column] else None)
            )
    return {
        i: {value_at(past[i][slot], 4, current[i].get(slot)) for slot in current[i].keys() | past[i].keys()} - {None}
        for i in range(1, 494)
    }


def _compare_profiles(data: HgssPokemon, api: PokeApi) -> list[dict]:
    types = _historical_slots(api, "pokemon_types", "type_id")
    past_types: dict[int, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    for row in api.table("pokemon_types_past"):
        past_types[int(row["pokemon_id"])][int(row["generation_id"])].add(int(row["type_id"]))
    for species_id, generations in past_types.items():
        for until in sorted(generations):
            if until >= 4:
                types[species_id] = generations[until]
                break
    abilities = _historical_slots(api, "pokemon_abilities", "ability_id")
    species = api.by_id("pokemon_species")
    ids = {
        table: {r["identifier"].upper().replace("-", ""): int(r["id"]) for r in api.table(table)}
        for table in ("types", "abilities")
    }
    differences = []
    for i, row in enumerate(data.personal[1:494], 1):
        for field, table, prefix, expected in (
            ("types", "types", "TYPE_", types[i]),
            ("abilities", "abilities", "ABILITY_", abilities[i]),
        ):
            native = {ids[table][v.removeprefix(prefix).replace("_", "")] for v in row[field] if v != prefix + "NONE"}
            if native != expected:
                differences.append(dict(species=i, field=field, native=sorted(native), pokeapi=sorted(expected)))
        for field, column in (
            ("catchRate", "capture_rate"),
            ("eggCycles", "hatch_counter"),
            ("friendship", "base_happiness"),
        ):
            if row[field] != int(species[i][column]):
                differences.append(dict(species=i, field=field, native=row[field], pokeapi=int(species[i][column])))
    return differences
