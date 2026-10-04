import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.maps import build_maps  # noqa: E402
from pokemaps_data.pokeapi import PokeApi  # noqa: E402
from pokemaps_data.sources import fetch_pokeapi_csv  # noqa: E402
from pokemaps_data.sprites import build_sprites  # noqa: E402

CACHE = TOOLS / ".cache"


@pytest.fixture(scope="session")
def assets_root(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("assets")


@pytest.fixture(scope="session")
def builder(assets_root) -> DatabaseBuilder:
    map_data = build_maps(CACHE, assets_root / "maps")
    return DatabaseBuilder(PokeApi(fetch_pokeapi_csv(CACHE)), map_data=map_data)


@pytest.fixture(scope="session")
def assets(builder, assets_root) -> Path:
    root = assets_root
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
