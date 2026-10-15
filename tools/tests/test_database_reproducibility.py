"""Le numéro du moteur SQLite ne doit pas modifier l'asset généré."""

import sqlite3
from contextlib import closing
from pathlib import Path

from pokemaps_data.builder import DatabaseBuilder


class _EmptyBuilder(DatabaseBuilder):
    def __init__(self) -> None:
        pass

    def tables(self, item_sprites: set[str]) -> dict[str, list[tuple]]:
        return {}


def test_database_header_is_independent_of_sqlite_version(tmp_path: Path) -> None:
    output = tmp_path / "pokedex.db"
    _EmptyBuilder().write(output, set())
    assert output.read_bytes()[96:100] == bytes(4)
    with closing(sqlite3.connect(output)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
