"""Données Pokémon d'Or et d'Argent (phase 1 de plan_gen_2.md) : tables construites depuis PokéAPI et pret.

Or et Argent ne sont pas encore dans games.GAMES : leurs tables sont construites à part (gold_silver_builder),
sans cartes, et comparées aux données de base du désassemblage pokegold.
"""

from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import Game, PretFormat
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.pret_identifiers import species_identifier
from pokemaps_data.pret_source import annotated_lines, macro_args
from pokemaps_data.sources import POKESPRITE_COMMIT
from pokemaps_data.sprites import _item_icon_paths

GOLD, SILVER = 4, 5
GEN2 = 2
STATS = ("hp", "attack", "defense", "speed", "special-attack", "special-defense")  # ordre des données de base pret
PIKACHU, CHANSEY, EEVEE, ESPEON, UMBREON, BLISSEY, STEELIX, ONIX, MEWTWO = 25, 113, 133, 196, 197, 242, 208, 95, 150
PICHU, CLEFFA, IGGLYBUFF, CHIKORITA, CHARIZARD = 172, 173, 174, 152, 6
FIRE_PUNCH, ZAP_CANNON, SWAGGER, THIEF, PROTECT, ICY_WIND, CURSE = 7, 192, 207, 168, 182, 196, 174


def _species(builder: DatabaseBuilder) -> dict[str, int]:
    return {row["identifier"]: species_id for species_id, row in builder.species.items()}


def _pret_base_data(repo: Gen2PretRepo) -> dict[str, tuple[list[int], list[str]]]:
    """Pokémon -> (stats dans l'ordre des données de base, types), lus dans data/pokemon/base_stats."""
    result = {}
    for path in sorted(repo.path("data/pokemon/base_stats").glob("*.asm")):
        lines = [code for code, _ in annotated_lines(path) if code.startswith("db ")]
        species, stats, types = (macro_args(line, "db") for line in lines[:3])
        type_names = [name.removesuffix("_TYPE").lower() for name in dict.fromkeys(types)]
        result[species[0]] = ([int(value) for value in stats], type_names)
    return result


def test_stats_and_types_match_the_game(gold_silver_builder: DatabaseBuilder, gold_silver_repo: Gen2PretRepo) -> None:
    builder = gold_silver_builder
    species = _species(builder)
    stat_names = {row[0]: row[1] for row in builder.pokemon.stat_table()}
    type_names = {row[0]: row[1] for row in builder.type_table()}
    stats: dict[int, dict[str, int]] = {}
    for pokemon, generation, stat, value in builder.pokemon.pokemon_stat_table():
        if generation == GEN2:
            stats.setdefault(pokemon, {})[stat_names[stat]] = value
    types: dict[int, list[str]] = {}
    for pokemon, generation, _slot, type_id in builder.pokemon.pokemon_type_table():
        if generation == GEN2:
            types.setdefault(pokemon, []).append(type_names[type_id])
    pret = _pret_base_data(gold_silver_repo)
    assert len(pret) == 251
    for const, (pret_stats, pret_types) in pret.items():
        pokemon = species[species_identifier(const)]
        assert [stats[pokemon][name] for name in STATS] == pret_stats, const
        assert types[pokemon] == pret_types, const


def test_second_generation_types_and_chart(gold_silver_builder: DatabaseBuilder) -> None:
    types = {row[1]: row[0] for row in gold_silver_builder.type_table()}
    # 17 types, plus « ??? », celui de Malédiction en 2e génération, hors du tableau des types.
    assert len(types) == 18
    assert "fairy" not in types
    assert gold_silver_builder.moves.types_outside_the_chart == {types["unknown"]}
    curse_type = {row[2] for row in gold_silver_builder.moves.move_version_group_table() if row[0] == CURSE}
    assert curse_type == {types["unknown"]}
    assert not [row for row in gold_silver_builder.type_efficacy_table() if types["unknown"] in row[1:3]]
    chart = {
        (attacking, defending): factor
        for generation, attacking, defending, factor in gold_silver_builder.type_efficacy_table()
        if generation == GEN2
    }

    def factor(attacking: str, defending: str) -> int:
        return chart[(types[attacking], types[defending])]

    # Changements de la 2e génération : Spectre efficace sur Psy, Insecte peu efficace sur Poison, Glace sur Feu.
    assert factor("ghost", "psychic") == 200
    assert factor("bug", "poison") == 50
    assert factor("poison", "bug") == 100
    assert factor("ice", "fire") == 50
    assert factor("steel", "rock") == 200
    assert factor("dark", "psychic") == 200
    assert factor("psychic", "dark") == 0


def test_evolutions_of_the_second_generation(gold_silver_builder: DatabaseBuilder) -> None:
    items = {row[0]: row[1] for row in gold_silver_builder.items.item_rows}
    rows = {(row[2], row[3]): row[4:] for row in gold_silver_builder.pokemon.evolution_rows}
    # (déclencheur, niveau, objet utilisé, objet tenu, bonheur, moment, attaque connue, échange contre)
    assert rows[(EEVEE, ESPEON)] == ("level-up", None, None, None, 220, "day", None, None)
    assert rows[(EEVEE, UMBREON)] == ("level-up", None, None, None, 220, "night", None, None)
    assert rows[(CHANSEY, BLISSEY)] == ("level-up", None, None, None, 220, None, None, None)
    trigger, *_, held, _happiness, _time, _move, _trade = rows[(ONIX, STEELIX)]
    assert (trigger, items[held]) == ("trade", "metal-coat")
    # Bébés : ils évoluent par bonheur vers un Pokémon de la 1re génération.
    for baby, adult in ((PICHU, PIKACHU), (CLEFFA, 35), (IGGLYBUFF, 39)):
        assert rows[(baby, adult)][0] == "level-up"
        assert rows[(baby, adult)][4] == 220


def test_happiness_threshold_comes_from_the_game(gold_silver_repo: Gen2PretRepo) -> None:
    # PokéAPI donne 160, le seuil des jeux récents : le moteur d'Or et d'Argent demande 220.
    assert gold_silver_repo.happiness_to_evolve == 220


def test_wild_held_items_follow_the_battle_engine(gold_silver_builder: DatabaseBuilder) -> None:
    items = {row[0]: row[1] for row in gold_silver_builder.items.item_rows}
    held = {
        (pokemon, version, items[item]): rarity
        for pokemon, version, item, rarity in (gold_silver_builder.items.pokemon_item_rows)
    }
    # Leveinard : aucun objet 1, Œuf Chance en objet 2 (2 %) ; Pikachu : la Baie (Baie Oran pour PokéAPI) à 2 %.
    assert held[(CHANSEY, GOLD, "lucky-egg")] == 2
    assert held[(PIKACHU, SILVER, "oran-berry")] == 2
    # Objet 1 : 23 % ; quand les deux objets sont les mêmes, les deux probabilités s'ajoutent (25 %).
    rarities = {rarity for _, _, _, rarity in gold_silver_builder.items.pokemon_item_rows}
    assert rarities <= {2, 23, 25}
    # ADN Berzerk, objet 2 de Mewtwo absent de PokéAPI : ajouté par tools/data/extra_items.csv.
    assert held[(MEWTWO, GOLD, "berserk-gene")] == 2


def test_move_effect_chances_come_from_the_move_table(gold_silver_builder: DatabaseBuilder) -> None:
    effects = {(row[0], row[1]): (row[7], row[8]) for row in gold_silver_builder.moves.move_version_group_table()}
    gold_silver = 3
    # « n percent » vaut n * 255 // 100 sur 256 : 10 % -> 25/256 ; 100 % -> 255/256 (le tirage peut valoir 255).
    assert effects[(FIRE_PUNCH, gold_silver)][1] == pytest.approx(25 / 256 * 100)
    assert effects[(ZAP_CANNON, gold_silver)][1] == pytest.approx(255 / 256 * 100)
    assert effects[(THIEF, gold_silver)][1] == pytest.approx(255 / 256 * 100)
    assert effects[(ICY_WIND, gold_silver)][1] == pytest.approx(255 / 256 * 100)
    # Vantardise : 100 % écrit dans la table, mais son script ne tire pas la probabilité (effet systématique).
    assert effects[(SWAGGER, gold_silver)] == (
        "Augmente l’Attaque de la cible de deux niveaux et la rend confuse.",
        None,
    )
    assert effects[(PROTECT, gold_silver)][0].startswith("Agit en premier")
    assert all(text for text, _ in effects.values())


def test_egg_and_tutor_moves_are_kept(gold_silver_builder: DatabaseBuilder) -> None:
    egg = {
        move
        for pokemon, _vg, move, method, _level in gold_silver_builder.moves.pokemon_move_rows
        if pokemon == CHIKORITA and method == "egg"
    }
    assert egg == {22, 68, 73, 175, 246}  # Fouet Lianes, Riposte, Vampigraine, Fléau, Pouvoir Antique
    # Cristal ajoute les attaques du tuteur (ici sans désassemblage : seules ses attaques sont construites).
    crystal = DatabaseBuilder(gold_silver_builder.api, games=(Game("crystal", "", (), "", (), PretFormat.GEN2, ()),))
    tutor = {(pokemon, move) for pokemon, _vg, move, method, _ in crystal.moves.pokemon_move_rows if method == "tutor"}
    assert (CHARIZARD, 53) in tutor  # Lance-Flammes


def test_johto_pokedex_and_descriptions(gold_silver_builder: DatabaseBuilder) -> None:
    builder = gold_silver_builder
    assert [row[1] for row in builder.pokedex_table()] == ["original-johto"]
    entries = builder.pokedex_entry_table()
    assert len(entries) == 251
    assert (3, CHIKORITA, 1) in entries
    # Aucune description française de la 2e génération dans PokéAPI : chaque Pokémon garde la plus ancienne.
    assert all(row[16] for row in builder.pokemon.pokemon_table())


def test_apricorn_balls_and_covers(gold_silver_builder: DatabaseBuilder) -> None:
    balls = {row[1] for row in gold_silver_builder.items.item_rows if row[3] == "apricorn-balls"}
    assert balls == {"level-ball", "lure-ball", "moon-ball", "friend-ball", "love-ball", "heavy-ball", "fast-ball"}
    covers = {row[1]: row[4] for row in gold_silver_builder.version_table()}
    assert covers == {"gold": 250, "silver": 249}  # Ho-Oh et Lugia


def test_every_item_has_an_icon(gold_silver_builder: DatabaseBuilder, tmp_path_factory: pytest.TempPathFactory) -> None:
    cache = Path(__file__).resolve().parent.parent / ".cache"
    assert (cache / f"pokesprite-{POKESPRITE_COMMIT[:12]}/data/item-map.json").is_file()
    icons = _item_icon_paths(gold_silver_builder, cache)
    # Les objets absents de PokéAPI (extra_items.csv : ADN Berzerk) n'existent que dans des jeux sans icônes d'objets.
    extra = {item.identifier for item in gold_silver_builder.items.extra_items.values()}
    assert {row[1] for row in gold_silver_builder.items.item_rows} - extra <= icons.keys()
    assert not extra & icons.keys()
    # CT03 Malédiction, de type « ??? » : pokesprite n'a pas d'icône de CT pour ce type.
    assert icons["tm03"] == "items/tm/normal.png"
