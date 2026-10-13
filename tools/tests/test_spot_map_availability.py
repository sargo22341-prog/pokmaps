"""Cartes propres à une version : sélection du plan et sauvegarde sans faux blocage."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from pokemaps_data.map_spots import Point, TerrainKey, read_spots
from spot_editor.catalog import EditorCatalog, Family
from spot_editor.session import SpotSession
from spot_editor.terrain import WildTerrains
from spot_editor.validation import save_spots, spot_errors

HOENN = Family("ruby-sapphire-emerald", "Rubis, Saphir et Émeraude", ("ruby-sapphire", "emerald"))
POINT = (8, 8)


@pytest.fixture
def catalog(database: Path) -> Iterator[EditorCatalog]:
    current = EditorCatalog(database)
    try:
        yield current
    finally:
        current.close()


class UniqueMapTerrain:
    def __init__(self, group: str) -> None:
        self.group = group

    def kinds(self, family: Family, _identifier: str) -> frozenset[str]:
        return frozenset({"underwater"}) if family.version_groups == (self.group,) else frozenset()

    def points(self, family: Family, _identifier: str, _kind: str) -> frozenset[Point]:
        assert family.version_groups == (self.group,)
        return frozenset({POINT})

    def rejected_versions(self, family: Family, _identifier: str, _kind: str, _point: Point) -> tuple[str, ...]:
        assert family.version_groups == (self.group,)
        return (self.group,)


@pytest.mark.parametrize("identifier,group", [("underwater1", "ruby-sapphire"), ("underwater-route124", "emerald")])
def test_unique_underwater_map_is_offered_only_in_its_game(catalog: EditorCatalog, identifier: str, group: str) -> None:
    assert catalog.available_groups(HOENN, identifier) == (group,)
    assert catalog.available_groups(HOENN, identifier) == (group,)
    assert catalog.version_map(HOENN, identifier, group) is not None
    other = next(found for found in HOENN.version_groups if found != group)
    assert catalog.version_map(HOENN, identifier, other) is None


def test_shared_map_keeps_both_plans_and_unknown_map_has_none(catalog: EditorCatalog) -> None:
    assert catalog.available_groups(HOENN, "route124") == HOENN.version_groups
    assert catalog.available_groups(HOENN, "unknown-map") == ()


@pytest.mark.parametrize("identifier,group", [("underwater1", "ruby-sapphire"), ("underwater-route124", "emerald")])
def test_common_points_on_unique_map_can_be_saved(
    catalog: EditorCatalog, tmp_path: Path, identifier: str, group: str
) -> None:
    key = TerrainKey(HOENN.identifier, identifier, "underwater")
    session = SpotSession({})
    session.toggle(key, frozenset(), POINT, lambda _point: False)
    terrains = UniqueMapTerrain(group)
    assert spot_errors(session, [HOENN], terrains, catalog) == []
    path = tmp_path / "map_spots.csv"
    save_spots(session, [HOENN], terrains, path, catalog)
    assert read_spots(path) == {key: frozenset({POINT})}
    assert not session.has_changes


def test_actual_invalid_point_on_unique_map_still_blocks_save(catalog: EditorCatalog, tmp_path: Path) -> None:
    key = TerrainKey(HOENN.identifier, "underwater1", "underwater")
    session = SpotSession({})
    session.toggle(key, frozenset(), (24, 8), lambda _point: False)
    path = tmp_path / "map_spots.csv"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(ValueError, match="Case non retenue"):
        save_spots(session, [HOENN], UniqueMapTerrain("ruby-sapphire"), path, catalog)
    assert path.read_text(encoding="utf-8") == "original"
    assert session.has_changes


def test_explicitly_wrong_game_is_distinct_from_missing_wild_pokemon(catalog: EditorCatalog) -> None:
    key = TerrainKey(HOENN.identifier, "underwater1", "underwater", "emerald")
    [error] = spot_errors(SpotSession({key: frozenset({POINT})}), [HOENN], UniqueMapTerrain("ruby-sapphire"), catalog)
    assert error.message == "Carte absente des jeux ciblés"


def test_common_points_overridden_in_the_only_existing_game_are_not_validated(catalog: EditorCatalog) -> None:
    common = TerrainKey(HOENN.identifier, "underwater1", "underwater")
    scoped = TerrainKey(HOENN.identifier, common.map_identifier, common.kind, "ruby-sapphire")
    session = SpotSession({common: frozenset({(24, 8)}), scoped: frozenset({POINT})})
    assert spot_errors(session, [HOENN], UniqueMapTerrain("ruby-sapphire"), catalog) == []


@pytest.mark.usefixtures("source_cache_ready")
@pytest.mark.parametrize("identifier,group", [("underwater1", "ruby-sapphire"), ("underwater-route124", "emerald")])
def test_pinned_underwater_points_save_without_validating_the_absent_plan(
    catalog: EditorCatalog, tmp_path: Path, identifier: str, group: str
) -> None:
    terrains = WildTerrains(Path(__file__).resolve().parents[1] / ".cache")
    present = Family(HOENN.identifier, HOENN.label, (group,))
    valid = terrains.points(present, identifier, "underwater")
    assert valid
    point = min(valid)
    key = TerrainKey(HOENN.identifier, identifier, "underwater")
    session = SpotSession({})
    session.toggle(key, frozenset(), point, lambda _point: False)
    assert spot_errors(session, [HOENN], terrains, catalog) == []
    path = tmp_path / "map_spots.csv"
    save_spots(session, [HOENN], terrains, path, catalog)
    assert read_spots(path) == {key: frozenset({point})}
