"""Portée des emplacements : CSV, édition, validation et application aux groupes de versions."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemaps_data.builder_maps import _SpotRows
from pokemaps_data.games import GAMES
from pokemaps_data.map_spots import TerrainKey, read_spots, write_spots
from spot_editor.catalog import Family
from spot_editor.session import SpotSession
from spot_editor.validation import spot_errors

COMMON = TerrainKey("red-blue-yellow", "route-1", "grass")
YELLOW = TerrainKey(COMMON.family, COMMON.map_identifier, COMMON.kind, "yellow")
RED = TerrainKey(COMMON.family, COMMON.map_identifier, COMMON.kind, "red-blue")
FAMILY = Family(COMMON.family, "Rouge, Bleu et Jaune", ("red-blue", "yellow"))
RED_POINT = (8, 8)
YELLOW_POINT = (24, 8)


class VersionTerrains:
    def kinds(self, _family: Family, _identifier: str) -> frozenset[str]:
        return frozenset({"grass"})

    def points(self, family: Family, _identifier: str, _kind: str) -> frozenset[tuple[int, int]]:
        if family.version_groups == ("red-blue",):
            return frozenset({RED_POINT})
        if family.version_groups == ("yellow",):
            return frozenset({YELLOW_POINT})
        return frozenset()

    def rejected_versions(self, family: Family, identifier: str, kind: str, point: tuple[int, int]) -> tuple[str, ...]:
        return tuple(
            group
            for group in family.version_groups
            if point not in self.points(Family(family.identifier, family.label, (group,)), identifier, kind)
        )


def test_scoped_csv_preserves_common_points_and_empty_overrides(tmp_path: Path) -> None:
    path = tmp_path / "map_spots.csv"
    spots = {COMMON: frozenset({RED_POINT}), YELLOW: frozenset({YELLOW_POINT}), RED: frozenset()}
    write_spots(spots, path)
    assert read_spots(path) == spots
    assert path.read_text(encoding="utf-8").splitlines()[0].endswith(",version_group")


def test_scoped_csv_rejects_a_group_from_another_family(tmp_path: Path) -> None:
    path = tmp_path / "map_spots.csv"
    path.write_text(
        "family,map_identifier,kind,x,y,version_group\nred-blue-yellow,route-1,grass,8,8,crystal\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="incompatible"):
        read_spots(path)


def test_specific_edit_inherits_common_points_and_keeps_other_group() -> None:
    session = SpotSession({COMMON: frozenset({RED_POINT})})
    inherited = session.effective_points(YELLOW, frozenset())
    session.toggle(YELLOW, inherited, YELLOW_POINT, lambda _point: False)
    session.remove(YELLOW, inherited, RED_POINT)
    assert session.effective_points(YELLOW, frozenset()) == {YELLOW_POINT}
    assert session.effective_points(RED, frozenset()) == {RED_POINT}
    assert session.merged() == {COMMON: frozenset({RED_POINT}), YELLOW: frozenset({YELLOW_POINT})}


def test_common_validation_ignores_a_group_with_its_own_override() -> None:
    session = SpotSession({COMMON: frozenset({RED_POINT}), YELLOW: frozenset({YELLOW_POINT})})
    assert spot_errors(session, [FAMILY], VersionTerrains()) == []
    session = SpotSession({COMMON: frozenset({RED_POINT})})
    [error] = spot_errors(session, [FAMILY], VersionTerrains())
    assert error.key == COMMON
    assert "yellow" in error.message


def test_builder_applies_only_the_selected_group_override() -> None:
    rows = _SpotRows({COMMON: frozenset({RED_POINT}), YELLOW: frozenset({YELLOW_POINT})}, GAMES)
    for group, point, map_id in (("red-blue", RED_POINT, 1), ("yellow", YELLOW_POINT, 2)):
        data = SimpleNamespace(
            maps=[SimpleNamespace(const="ROUTE_1")],
            spots=[SimpleNamespace(map_const="ROUTE_1", kind="grass", x=point[0], y=point[1])],
            terrain={("route-1", "grass"): frozenset({point})},
        )
        rows.add_game(group, data, {"ROUTE_1": map_id})
    rows.check_all_used({COMMON.family})
    assert rows.rows == [(1, 1, "grass", *RED_POINT), (2, 2, "grass", *YELLOW_POINT)]


def test_builder_empty_override_removes_only_yellow_points() -> None:
    rows = _SpotRows({YELLOW: frozenset()}, GAMES)
    data = SimpleNamespace(
        maps=[SimpleNamespace(const="ROUTE_1")],
        spots=[SimpleNamespace(map_const="ROUTE_1", kind="grass", x=8, y=8)],
        terrain={("route-1", "grass"): frozenset({RED_POINT})},
    )
    rows.add_game("red-blue", data, {"ROUTE_1": 1})
    rows.add_game("yellow", data, {"ROUTE_1": 2})
    assert rows.rows == [(1, 1, "grass", *RED_POINT)]


def test_common_points_shadowed_in_every_group_are_not_reported_as_unknown() -> None:
    rows = _SpotRows({COMMON: frozenset({(1000, 1000)}), RED: frozenset(), YELLOW: frozenset()}, GAMES)
    data = SimpleNamespace(
        maps=[SimpleNamespace(const="ROUTE_1")],
        spots=[SimpleNamespace(map_const="ROUTE_1", kind="grass", x=8, y=8)],
        terrain={("route-1", "grass"): frozenset({RED_POINT})},
    )
    rows.add_game("red-blue", data, {"ROUTE_1": 1})
    rows.add_game("yellow", data, {"ROUTE_1": 2})
    rows.check_all_used({COMMON.family})
    assert rows.rows == []
