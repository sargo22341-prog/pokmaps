import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.sources import PRET_RED_BLUE, PRET_YELLOW, fetch_git, fetch_pokeapi_csv  # noqa: E402

CACHE = TOOLS / ".cache"


@pytest.fixture(scope="session")
def sources() -> tuple[Path, Path, Path]:
    return fetch_git(PRET_RED_BLUE, CACHE), fetch_git(PRET_YELLOW, CACHE), fetch_pokeapi_csv(CACHE)


@pytest.fixture(scope="session")
def database(sources, tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("db") / "pokedex.db"
    DatabaseBuilder(*sources).write(path)
    return path


@pytest.fixture()
def db(database):
    connection = sqlite3.connect(database)
    yield connection
    connection.close()
