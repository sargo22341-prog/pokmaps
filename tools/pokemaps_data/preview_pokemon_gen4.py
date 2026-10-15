"""Aperçu Pokémon DS sans cartes ni effets de combat (phases suivantes), indépendant des assets livrés."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from .asset_manifest import write_manifest
from .builder import SCHEMA, SCHEMA_VERSION, DatabaseBuilder
from .builder_forms import form_table
from .encounter_methods_gen4 import check_encounter_taxonomy
from .games import GEN4_GAMES
from .pokeapi import PokeApi
from .pret_evolution_gen4 import compare_ds_evolutions
from .pret_items_gen4 import ds_item_constants, ds_item_id
from .pret_pokemon_moves_gen4 import read_ds_moves
from .preview_encounters_gen4 import complete_preview_encounters
from .sources import fetch_pokeapi_csv, fetch_pret
from .sprites import build_sprites
from .validate import _check_obtainable


def build_pokemon_preview(cache: Path, output: Path, assets: Path) -> None:
    target = (output / "sinnoh-pokemon").resolve()
    source = assets.resolve()
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("L'aperçu Pokémon DS doit être séparé des assets de l'application")
    roots = {g.version_group: fetch_pret(cache, g.pret_repo) for g in GEN4_GAMES}
    builder = DatabaseBuilder(PokeApi(fetch_pokeapi_csv(cache)), GEN4_GAMES, pret_roots=roots)
    compare_ds_evolutions(builder)
    for game in GEN4_GAMES:
        for const in ds_item_constants(roots[game.version_group], game.pret_repo):
            ds_item_id(builder, const)
    output = output / "sinnoh-pokemon"
    output.mkdir(parents=True, exist_ok=True)
    sprites = build_sprites(builder, cache, output / "sprites")
    if missing := {row[1] for row in builder.items.item_rows} - sprites:
        raise ValueError(f"Icônes d'objets manquantes dans l'aperçu DS : {sorted(missing)}")
    tables = pokemon_preview_tables(builder, sprites)
    path = output / "database/pokedex.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Remplacer atomiquement la base évite de laisser un ancien aperçu en cas d'échec.
    temporary = path.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    with closing(sqlite3.connect(temporary)) as connection, connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.execute(
            "CREATE TABLE ds_move (move_id INTEGER, version_group_id INTEGER, power INTEGER, "
            "pp INTEGER, accuracy INTEGER, type_id INTEGER, damage_class TEXT, "
            "PRIMARY KEY(move_id, version_group_id))"
        )
        for table, rows in tables.items():
            if rows:
                marks = ",".join("?" * len(rows[0]))
                connection.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        errors = validate_pokemon_preview(connection)
        if errors:
            raise ValueError("Aperçu Pokémon DS invalide : " + "; ".join(errors))
        connection.commit()
        connection.execute("VACUUM")
    with temporary.open("r+b") as handle:
        handle.seek(96)
        handle.write(bytes(4))
    temporary.replace(path)
    shutil.copytree(assets / "licenses", output / "licenses", dirs_exist_ok=True)
    write_manifest(output)
    print(f"Aperçu Pokémon DS validé : {output} (493 espèces, 3 versions)")


def pokemon_preview_tables(builder: DatabaseBuilder, sprites: set[str]) -> dict[str, list[tuple]]:
    check_encounter_taxonomy(builder)
    complete_preview_encounters(builder)
    encounters, conditions = builder.encounters.encounter_tables()
    descriptions = builder.items.item_descriptions()
    moves = ds_move_rows(builder)
    return {
        "generation": builder.generation_table(),
        "region": builder.region_table(),
        "version_group": builder.version_group_table(),
        "version": builder.version_table(),
        "pokedex": builder.pokedex_table(),
        "version_group_pokedex": builder.pokedex_links,
        "pokedex_entry": builder.pokedex_entry_table(),
        "type": builder.type_table(),
        "type_efficacy": builder.type_efficacy_table(),
        "stat": builder.pokemon.stat_table(),
        "growth_rate": builder.pokemon.growth_rate_table(),
        "pokemon": builder.pokemon.pokemon_table(),
        "pokemon_version_group": builder.pokemon.pokemon_version_group_rows(),
        "pokemon_form": form_table(builder),
        "pokemon_type": builder.pokemon.pokemon_type_table(),
        "pokemon_stat": builder.pokemon.pokemon_stat_table(),
        "move": _preview_moves(builder, moves),
        "ds_move": moves,
        "machine": builder.moves.machine_rows,
        "pokemon_move": builder.moves.pokemon_move_table(),
        "item": [(*r, int(r[1] in sprites), descriptions.get(r[0])) for r in builder.items.item_rows],
        "pokemon_item": builder.items.pokemon_item_rows,
        "egg_group": builder.pokemon.egg_group_table(),
        "pokemon_egg_group": builder.pokemon.egg_group_rows,
        "ability": builder.abilities.ability_table(),
        "ability_version_group": builder.abilities.ability_version_group_table(),
        "pokemon_ability": builder.abilities.pokemon_ability_rows,
        "evolution": builder.pokemon.evolution_rows,
        "evolution_requirement": builder.pokemon.evolution_requirement_rows,
        "location": builder.locations.location_rows(builder.encounters.used_areas),
        "location_area": builder.locations.location_area_table(builder.encounters.used_areas),
        "encounter_method": builder.encounters.encounter_method_table(),
        "encounter_condition_value": builder.encounters.encounter_condition_value_table(),
        "encounter": encounters,
        "encounter_condition": conditions,
    }


def _preview_moves(builder: DatabaseBuilder, rows: list[tuple]) -> list[tuple]:
    # Lutte n'est jamais apprise, mais reste une attaque du moteur et du catalogue DS.
    names = builder.api.names("move_names", "move_id")
    moves = builder.api.by_id("moves")
    return [(i, moves[i]["identifier"], names[i], int(moves[i]["generation_id"])) for i in sorted({r[0] for r in rows})]


def ds_move_rows(builder: DatabaseBuilder) -> list[tuple]:
    types = {r["identifier"]: int(r["id"]) for r in builder.api.table("types")}
    moves = builder.api.by_id("moves")
    result = []
    for vg in builder.vg_ids:
        game = builder.game_of(vg)
        for row in read_ds_moves(builder.pret_root(game, "les attaques DS"), game.pret_repo):
            move = builder.moves.move_id(row.identifier)
            if builder.moves._damage_class(vg, moves[move], types[row.type]) != row.damage_class:
                raise ValueError(f"Classe d'attaque PokéAPI différente de pret : {game.version_group}/{row.identifier}")
            result.append((move, vg, row.power, row.pp, row.accuracy, types[row.type], row.damage_class))
    return result


def validate_pokemon_preview(connection: sqlite3.Connection) -> list[str]:
    from .validate import CHECKS
    from .validate_profiles import validate_profiles

    # Les invariants de cartes et d'effets appartiennent aux phases 2–5 ; les autres restent identiques.
    excluded = {
        "attaque sans caractéristiques dans le jeu",
        "effet d'attaque vide ou probabilité invalide",
        "zone avec des rencontres sans carte dans le jeu",
        "probabilités de rencontre aléatoire différentes de 100 %",
    }
    errors = []
    for label, query in CHECKS:
        if label not in excluded and (rows := connection.execute(query).fetchall()):
            errors.append(f"{label} : {rows[:5]}")
    errors += validate_profiles(connection)
    errors += _check_obtainable(connection)
    invalid = connection.execute(
        "SELECT d.move_id FROM ds_move d LEFT JOIN move m ON m.id = d.move_id "
        "WHERE m.id IS NULL OR d.power NOT BETWEEN 0 AND 255 OR d.pp NOT BETWEEN 1 AND 40 "
        "OR d.accuracy NOT BETWEEN 0 AND 100 OR d.damage_class NOT IN ('status', 'physical', 'special') "
        "OR d.version_group_id NOT IN (SELECT id FROM version_group) OR d.type_id NOT IN (SELECT id FROM type)"
    ).fetchall()
    if invalid:
        errors.append(f"Caractéristiques DS invalides : {invalid[:5]}")
    if connection.execute(
        "SELECT 1 FROM pokemon_move p WHERE NOT EXISTS (SELECT 1 FROM ds_move m "
        "WHERE m.move_id = p.move_id AND m.version_group_id = p.version_group_id)"
    ).fetchone():
        errors.append("Attaque apprise sans caractéristiques DS")
    return errors
