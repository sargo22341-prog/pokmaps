"""Métadonnées de présentation et capacités horaires des jeux."""

import re
import sqlite3
from pathlib import Path

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import FIRERED_LEAFGREEN, GAMES, GAMES_IN_PROGRESS, GEN3_GAMES, GEN4_GAMES, PretFormat
from pokemaps_data.validate import validate

_APP = Path(__file__).parents[2] / "app/src/main/java/org/opensources/pokmaps"
# Capacités de chaque version livrée : groupe, génération, format pret, famille de cartes, régions,
# Pokédex National débloqué et génération d'origine d'un remake.
_MATRIX = {
    "red": ("red-blue", 1, PretFormat.GEN1, "red-blue-yellow", ("KANTO",), False, None),
    "blue": ("red-blue", 1, PretFormat.GEN1, "red-blue-yellow", ("KANTO",), False, None),
    "yellow": ("yellow", 1, PretFormat.GEN1, "red-blue-yellow", ("KANTO",), False, None),
    "gold": ("gold-silver", 2, PretFormat.GEN2, "gold-silver-crystal", ("JOHTO", "KANTO"), False, None),
    "silver": ("gold-silver", 2, PretFormat.GEN2, "gold-silver-crystal", ("JOHTO", "KANTO"), False, None),
    "crystal": ("crystal", 2, PretFormat.GEN2, "gold-silver-crystal", ("JOHTO", "KANTO"), False, None),
    "ruby": ("ruby-sapphire", 3, PretFormat.GEN3, "ruby-sapphire-emerald", ("HOENN",), True, None),
    "sapphire": ("ruby-sapphire", 3, PretFormat.GEN3, "ruby-sapphire-emerald", ("HOENN",), True, None),
    "emerald": ("emerald", 3, PretFormat.GEN3, "ruby-sapphire-emerald", ("HOENN",), True, None),
    "firered": ("firered-leafgreen", 3, PretFormat.GEN3, "firered-leafgreen", ("KANTO", "SEVII"), True, 1),
    "leafgreen": ("firered-leafgreen", 3, PretFormat.GEN3, "firered-leafgreen", ("KANTO", "SEVII"), True, 1),
}


def test_capabilities_of_the_eleven_versions(db: sqlite3.Connection) -> None:
    assert GAMES_IN_PROGRESS == ()
    query = "SELECT v.identifier, vg.generation_id FROM version v JOIN version_group vg ON vg.id = v.version_group_id"
    generations = dict(db.execute(query))
    declared = {
        version: (
            game.version_group,
            generations[version],
            game.pret_format,
            game.map_family,
            tuple(region.const for region in game.regions),
            game.national_dex,
            game.remake_generation,
        )
        for game in GAMES
        for version, _ in game.pret_versions
    }
    assert declared == _MATRIX
    assert set(generations) == set(_MATRIX)


def test_app_version_groups_match_the_pipeline_families() -> None:
    source = (_APP / "domain/model/VersionGroup.kt").read_text(encoding="utf-8")
    entries = re.findall(r'^\s+[A-Z_]+\("([a-z-]+)", "([a-z-]+)"\)[,;]$', source, re.MULTILINE)
    # Les modèles DS sont prêts avant le passage des assets de Sinnoh dans GAMES.
    modeled = (*GAMES, *GEN4_GAMES)
    assert dict(entries) == {game.version_group: game.map_family for game in modeled}
    assert len(entries) == len(modeled)


def test_remake_generation_is_explicit() -> None:
    assert FIRERED_LEAFGREEN.remake_generation == 1
    assert [game.remake_generation for game in GEN3_GAMES] == [None, None, 1]


def test_remake_generation_is_exported(gen3_builder: DatabaseBuilder) -> None:
    rows = {row[1]: row[-1] for row in gen3_builder.version_group_table()}
    assert rows == {"ruby-sapphire": None, "emerald": None, "firered-leafgreen": 1}


def test_invalid_remake_generation_is_rejected(db: sqlite3.Connection, database: Path) -> None:
    db.execute("UPDATE version_group SET remake_generation_id = generation_id")
    db.commit()
    copied_database = Path(db.execute("PRAGMA database_list").fetchone()[2])
    assert copied_database != database
    assert any("génération d'origine du remake invalide" in error for error in validate(copied_database))


def test_game_query_derives_time_from_encounters(db: sqlite3.Connection) -> None:
    source = Path(__file__).parents[2] / "app/src/main/java/org/opensources/pokmaps/data/db/GameDao.kt"
    query = source.read_text(encoding="utf-8").split('"""')[1]
    rows = db.execute(query).fetchall()
    columns = [column[0] for column in db.execute(query).description]
    games = [dict(zip(columns, row, strict=True)) for row in rows]
    assert {game["versionIdentifier"] for game in games if game["hasTimeOfDay"]} == {"gold", "silver", "crystal"}
    db.execute("DELETE FROM encounter_condition")
    assert all(not row[columns.index("hasTimeOfDay")] for row in db.execute(query))
