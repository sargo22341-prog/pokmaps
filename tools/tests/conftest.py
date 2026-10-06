import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

from pokemaps_data import sources  # noqa: E402
from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.maps import build_maps  # noqa: E402
from pokemaps_data.pokeapi import PokeApi  # noqa: E402
from pokemaps_data.sources import PRET_COMMITS, fetch_pokeapi_csv  # noqa: E402
from pokemaps_data.sprites import build_sprites  # noqa: E402

CACHE = TOOLS / ".cache"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Les tests ne doivent pas accéder au réseau ; exécutez tools/build_data.py d'abord.")

    monkeypatch.setattr(sources.urllib.request, "urlopen", reject_network)


@pytest.fixture(scope="session")
def assets_root(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("assets")


@pytest.fixture(scope="session")
def builder(assets_root, source_cache_ready) -> DatabaseBuilder:
    map_data = build_maps(CACHE, assets_root / "maps")
    return DatabaseBuilder(PokeApi(fetch_pokeapi_csv(CACHE)), map_data=map_data)


@pytest.fixture(scope="session")
def source_cache_ready() -> None:
    missing = [
        repo for repo, commit in PRET_COMMITS.items() if not (CACHE / f"{repo}-{commit[:12]}" / ".complete").is_file()
    ]
    if missing:
        pytest.fail(
            f"Sources pret absentes : {missing}. Exécutez tools/build_data.py avant les tests.",
            pytrace=False,
        )


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
