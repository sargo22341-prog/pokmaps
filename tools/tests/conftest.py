import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from pokemaps_data import sources
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import GAMES, GOLD_SILVER
from pokemaps_data.maps import GameMapData, build_maps
from pokemaps_data.maps_layout import GameMaps, read_layout_curation
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.sources import PRET_COMMITS, fetch_pokeapi_csv, pret_dir
from pokemaps_data.sprites import build_sprites

TOOLS = Path(__file__).resolve().parent.parent
CACHE = TOOLS / ".cache"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Les tests ne doivent pas accéder au réseau ; exécutez tools/build_data.py d'abord.")

    monkeypatch.setattr(sources.urllib.request, "urlopen", reject_network)


@pytest.fixture(scope="session")
def assets_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("assets")


@pytest.fixture(scope="session")
def builder(assets_root: Path, source_cache_ready: None) -> DatabaseBuilder:
    map_data = build_maps(CACHE, assets_root / "maps")
    pret_roots = {game.version_group: pret_dir(CACHE, game.pret_repo) for game in GAMES}
    return DatabaseBuilder(PokeApi(fetch_pokeapi_csv(CACHE)), map_data=map_data, pret_roots=pret_roots)


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
def assets(builder: DatabaseBuilder, assets_root: Path) -> Path:
    root = assets_root
    item_sprites = build_sprites(builder, CACHE, root / "sprites")
    builder.write(root / "database/pokedex.db", item_sprites)
    return root


@pytest.fixture(scope="session")
def database(assets: Path) -> Path:
    return assets / "database/pokedex.db"


@pytest.fixture()
def db(database: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database)
    yield connection
    connection.close()


# --- Or et Argent (hors de GAMES : construits à part, cf. games.GOLD_SILVER) ------------------------------


@pytest.fixture(scope="session")
def gold_silver_repo(source_cache_ready: None) -> Gen2PretRepo:
    return Gen2PretRepo(pret_dir(CACHE, GOLD_SILVER.pret_repo), GOLD_SILVER.pret_versions)


@pytest.fixture(scope="session")
def gold_silver_builder(source_cache_ready: None) -> DatabaseBuilder:
    """Tables des Pokémon, des attaques et des objets d'Or et d'Argent, sans cartes."""
    pret_roots = {GOLD_SILVER.version_group: pret_dir(CACHE, GOLD_SILVER.pret_repo)}
    return DatabaseBuilder(PokeApi(fetch_pokeapi_csv(CACHE)), games=(GOLD_SILVER,), pret_roots=pret_roots)


@pytest.fixture(scope="session")
def gold_silver_maps(gold_silver_repo: Gen2PretRepo) -> GameMaps:
    return GameMaps(gold_silver_repo, GOLD_SILVER, read_layout_curation())


@pytest.fixture(scope="session")
def gold_silver_export(tmp_path_factory: pytest.TempPathFactory, source_cache_ready: None) -> tuple[GameMapData, Path]:
    """Cartes d'Or et d'Argent générées (lignes de la base et dossier des tuiles)."""
    output = tmp_path_factory.mktemp("gold-silver-maps")
    data = build_maps(CACHE, output, games=(GOLD_SILVER,))[GOLD_SILVER.version_group]
    return data, output / GOLD_SILVER.version_group
