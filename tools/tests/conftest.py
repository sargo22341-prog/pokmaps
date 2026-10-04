import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.pokeapi import PokeApi  # noqa: E402
from pokemaps_data.sources import fetch_pokeapi_csv  # noqa: E402
from pokemaps_data.sprites import build_sprites  # noqa: E402

CACHE = TOOLS / ".cache"


@pytest.fixture(scope="session")
def builder() -> DatabaseBuilder:
    return DatabaseBuilder(PokeApi(fetch_pokeapi_csv(CACHE)))


@pytest.fixture(scope="session")
def assets(builder, tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("assets")
    item_sprites = build_sprites(builder, CACHE, root / "sprites")
    builder.write(root / "database/pokedex.db", item_sprites)
    return root


@pytest.fixture(scope="session")
def database(assets) -> Path:
    return assets / "database/pokedex.db"


@pytest.fixture()
def db(database):
    connection = sqlite3.connect(database)
    yield connection
    connection.close()
