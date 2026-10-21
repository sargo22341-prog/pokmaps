"""Assemblage français du catalogue Pokémon préparatoire HGSS, sans lieux ni rencontres."""

from .evolution_hgss import evolution_rows
from .pokeapi import PokeApi
from .pret_hgss_pokemon import HgssPokemon


def french_constants(api: PokeApi) -> dict[str, str]:
    result = {}
    for table, names_table, column, prefix in (
        ("pokemon_species", "pokemon_species_names", "pokemon_species_id", "SPECIES_"),
        ("moves", "move_names", "move_id", "MOVE_"),
        ("items", "item_names", "item_id", "ITEM_"),
        ("abilities", "ability_names", "ability_id", "ABILITY_"),
        ("types", "type_names", "type_id", "TYPE_"),
    ):
        names = api.names(names_table, column)
        for row in api.table(table):
            if int(row["id"]) in names:
                result[prefix + row["identifier"].upper().replace("-", "_")] = names[int(row["id"])]
    aliases = {
        "ITEM_THUNDERSTONE": "ITEM_THUNDER_STONE",
        "ITEM_FIRESTONE": "ITEM_FIRE_STONE",
        "ITEM_WATERSTONE": "ITEM_WATER_STONE",
        "ITEM_LEAFSTONE": "ITEM_LEAF_STONE",
        "ITEM_DEEPSEATOOTH": "ITEM_DEEP_SEA_TOOTH",
        "ITEM_DEEPSEASCALE": "ITEM_DEEP_SEA_SCALE",
        "ITEM_KINGS_ROCK": "ITEM_KINGS_ROCK",
        "ITEM_UPGRADE": "ITEM_UP_GRADE",
    }
    for key, target in aliases.items():
        result[key] = result[target]
    return result


def pokemon_catalog(data: HgssPokemon, api: PokeApi, rules: dict, forms: list[dict]) -> dict:
    names = api.names("pokemon_species_names", "pokemon_species_id")
    moves = api.names("move_names", "move_id")
    if not set(range(1, 494)) <= names.keys() or not set(range(1, 468)) <= moves.keys():
        raise ValueError("HGSS : noms français Pokémon ou attaques incomplets")
    records = [
        dict(id=i, name_fr=names[i], regional=data.regional[i], personal=row, level_moves=data.level_moves[i])
        for i, row in enumerate(data.personal[1:494], 1)
    ]
    supplementary = [
        r
        for r in api.table("pokemon_moves")
        if r["version_group_id"] == "10"
        and int(r["pokemon_id"]) <= 493
        and r["pokemon_move_method_id"] not in {"1", "4"}
    ]
    return dict(
        versions=[
            dict(id=15, identifier="heartgold", name_fr="Or HeartGold"),
            dict(id=16, identifier="soulsilver", name_fr="Argent SoulSilver"),
        ],
        version_group=dict(id=10, identifier="heartgold-soulsilver", generation=4),
        pokemon=records,
        forms=forms,
        moves=[r | {"name_fr": moves[r["id"]]} for r in data.moves],
        machines=data.machines,
        tutors=data.tutors,
        evolutions=evolution_rows(data, rules, french_constants(api)),
        rules=rules,
        names_fr=french_constants(api),
        supplementary_moves=dict(source="PokéAPI épinglé, groupe 10 uniquement", rows=supplementary),
        special_forms=[
            dict(
                species=172,
                identifier="pichu-spiky",
                name_fr="Pichu Troizépi",
                personal_member=172,
                evolves=False,
                tradeable=False,
                sprite="sprites/pichu-spiky-hgss.png",
                sprite_style="HGSS native sheet",
            )
        ],
    )
