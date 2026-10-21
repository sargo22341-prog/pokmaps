"""Les fixtures ne refont pas les exports et gardent l'ordre des identifiants SQLite."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from pokemaps_data import maps_export_gen4
from pokemaps_data.games import CRYSTAL, GAMES, GEN4_GAMES, GOLD_SILVER, Game
from pokemaps_data.maps import GameMapData
from pokemaps_data.pokeapi import PokeApi

from . import conftest


@dataclass(frozen=True)
class _BuilderResult:
    api: PokeApi
    map_data: dict[str, GameMapData]


def test_combined_exports_preserve_production_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = PokeApi(tmp_path)
    data = {game.version_group: GameMapData([], [], [], []) for game in GAMES}
    calls: list[tuple[Game, ...]] = []

    def build_maps(cache: Path, output: Path, games: tuple[Game, ...], api: PokeApi) -> dict[str, GameMapData]:
        calls.append(games)
        return {game.version_group: data[game.version_group] for game in games}

    def builder(api: PokeApi, map_data: dict[str, GameMapData], pret_roots: dict[str, Path]) -> _BuilderResult:
        return _BuilderResult(api, map_data)

    def sinnoh(game: Game) -> GameMapData:
        return data[game.version_group]

    monkeypatch.setattr(conftest, "build_maps", build_maps)
    monkeypatch.setattr(conftest, "DatabaseBuilder", builder)
    legacy = {game.version_group: data[game.version_group] for game in (GOLD_SILVER, CRYSTAL)}
    # pytest expose le corps d'une fixture par __wrapped__, sans lancer ses dépendances réelles.
    result = conftest.builder.__wrapped__(tmp_path, (legacy, tmp_path), api, sinnoh)
    assert list(result.map_data) == [game.version_group for game in GAMES]
    assert result.api is api
    assert calls == [tuple(game for game in GAMES if game not in (GOLD_SILVER, CRYSTAL, *GEN4_GAMES))]


def test_sinnoh_exports_are_lazy_and_run_once_per_family(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = PokeApi(tmp_path)
    calls: list[tuple[Game, PokeApi]] = []

    def export(cache: Path, output: Path, game: Game, api: PokeApi) -> GameMapData:
        calls.append((game, api))
        return GameMapData([], [], [], [])

    monkeypatch.setattr(maps_export_gen4, "export_game", export)
    exports = conftest.sinnoh_exports.__wrapped__(tmp_path, api)
    assert calls == []
    first = exports(GEN4_GAMES[0])
    assert exports(GEN4_GAMES[0]) is first
    assert calls == [(GEN4_GAMES[0], api)]
    exports(GEN4_GAMES[1])
    assert calls == [(game, api) for game in GEN4_GAMES]
