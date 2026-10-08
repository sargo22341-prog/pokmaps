"""Règles de l'éditeur d'emplacements, sans fenêtre : catalogue, état d'édition et contrôles."""

from pathlib import Path

import pytest

from pokemaps_data.map_spots import TerrainKey, read_spots
from spot_editor.catalog import EditorCatalog, EditorMap, EncounterLine, Family, required_spots, used_by_app
from spot_editor.session import SpotSession, Toggle
from spot_editor.terrain import WildTerrains
from spot_editor.validation import save_spots

CACHE = Path(__file__).resolve().parent.parent / ".cache"

KEY = TerrainKey("red-blue-yellow", "route-1", "grass")
GENERATED = frozenset({(808, 3176), (856, 3224)})
ROUTE = EditorMap("red-blue-yellow", "route-1", "Route 1", "red-blue", (1012,), "kanto", 800, 3168, 320, 576)


def line(version: str, method: str, pokemon_id: int) -> EncounterLine:
    return EncounterLine(version, method, method, pokemon_id, str(pokemon_id), 2, 5, 10.0)


def never(_point: tuple[int, int]) -> bool:
    return False


def test_untouched_terrain_shows_generated_points() -> None:
    session = SpotSession({})
    assert session.points(KEY, GENERATED) == GENERATED
    assert not session.has_changes


def test_toggle_adds_then_removes_a_point() -> None:
    session = SpotSession({})
    assert session.toggle(KEY, GENERATED, (904, 3272), never) is Toggle.ADDED
    assert session.points(KEY, GENERATED) == GENERATED | {(904, 3272)}
    assert session.toggle(KEY, GENERATED, (0, 0), lambda point: point == (808, 3176)) is Toggle.REMOVED
    assert session.points(KEY, GENERATED) == {(856, 3224), (904, 3272)}


def test_undoing_an_edit_leaves_the_terrain_generated() -> None:
    session = SpotSession({})
    session.toggle(KEY, GENERATED, (904, 3272), never)
    session.toggle(KEY, GENERATED, (0, 0), lambda point: point == (904, 3272))
    assert not session.has_changes
    assert session.merged() == {}


def test_only_edited_terrains_are_written() -> None:
    other = TerrainKey("red-blue-yellow", "route-1", "floor")
    session = SpotSession({other: frozenset({(1, 1)})})
    session.clear(KEY, GENERATED)
    assert session.merged() == {other: frozenset({(1, 1)}), KEY: frozenset()}
    session.mark_written()
    assert not session.has_changes
    assert session.points(KEY, GENERATED) == frozenset()


def test_shortfalls_list_edited_terrains_with_too_few_points() -> None:
    session = SpotSession({})
    session.toggle(KEY, GENERATED, (904, 3272), never)
    assert session.shortfalls(lambda _key: ("Route 1", 3)) == []
    [shortfall] = session.shortfalls(lambda _key: ("Route 1", 4))
    assert (shortfall.map_name, shortfall.points, shortfall.required) == ("Route 1", 3, 4)


def test_required_spots_follow_the_app_grouping() -> None:
    lines = [
        line("Rouge", "walk", 16),
        line("Rouge", "walk", 19),
        line("Bleu", "walk", 16),
        line("Rouge", "surf", 72),
        line("Rouge", "old-rod", 129),
        line("Rouge", "super-rod", 129),
        line("Rouge", "good-rod", 72),
    ]
    assert required_spots(lines, "grass") == 2
    assert required_spots(lines, "floor") == 2
    # Surf et pêche partagent l'eau ; les trois cannes ne font qu'une méthode.
    assert required_spots(lines, "water") == 3
    assert required_spots([], "water") == 0


def test_headbutt_and_rock_smash_have_their_own_terrain() -> None:
    lines = [
        line("Or", "headbutt", 21),
        line("Or", "headbutt-high", 21),
        line("Or", "headbutt-high", 214),
        line("Or", "rock-smash", 98),
    ]
    # Arbres ordinaires et arbres rares ne font qu'une méthode, comme les trois cannes.
    assert required_spots(lines, "tree") == 2
    assert required_spots(lines, "rock") == 1
    assert required_spots(lines, "grass") == 0
    assert used_by_app("tree", has_grass=True, has_floor=False)
    assert used_by_app("rock", has_grass=True, has_floor=True)


def test_walking_uses_grass_before_floor() -> None:
    assert used_by_app("grass", has_grass=True, has_floor=True)
    assert not used_by_app("floor", has_grass=True, has_floor=True)
    assert used_by_app("floor", has_grass=False, has_floor=True)
    assert used_by_app("grass", has_grass=False, has_floor=False)
    assert used_by_app("water", has_grass=True, has_floor=False)


def test_snap_centers_points_on_cells_inside_the_place() -> None:
    assert ROUTE.snap(801, 3169) == (808, 3176)
    assert ROUTE.snap(831.9, 3200) == (824, 3208)
    assert ROUTE.snap(799, 3200) is None
    assert ROUTE.snap(1120, 3200) is None


def test_catalog_merges_the_games_of_a_family(database: Path) -> None:
    catalog = EditorCatalog(database)
    try:
        family = next(found for found in catalog.families() if found.identifier == "red-blue-yellow")
        assert family.label == "Rouge, Bleu et Jaune"
        assert family.version_groups == ("red-blue", "yellow")
        route = next(found for found in catalog.maps(family) if found.identifier == "route-1")
        assert len(route.map_ids) == 2
        assert route.displayed == "kanto"
        versions = {found.version for found in catalog.encounters(route)}
        assert versions == {"Rouge", "Bleu", "Jaune"}
        assert catalog.generated_spots(route)["grass"]
    finally:
        catalog.close()


def test_catalog_of_gold_and_silver_in_the_preview(preview_database: Path) -> None:
    catalog = EditorCatalog(preview_database)
    try:
        family = next(found for found in catalog.families() if found.identifier == "gold-silver-crystal")
        assert (family.label, family.version_groups) == ("Or, Argent et Cristal", ("gold-silver", "crystal"))
        assert catalog.world_names(family) == {"johto": "Johto", "kanto": "Kanto"}
        route = next(found for found in catalog.maps(family) if found.identifier == "route-29")
        assert route.displayed == "johto"
        assert catalog.generated_spots(route)["tree"]
        assert {line.method for line in catalog.encounters(route)} >= {"walk", "headbutt", "headbutt-high"}
        # Un seul Lugia dessiné : celui de la première version (Or), pas celui d'Argent au même endroit.
        chamber = next(found for found in catalog.maps(family) if found.identifier == "whirl-island-lugia-chamber")
        assert [mark.kind for mark in catalog.marks(chamber)].count("pokemon") == 1
    finally:
        catalog.close()


def test_every_place_belongs_to_a_region(preview_database: Path) -> None:
    catalog = EditorCatalog(preview_database)
    try:
        family = next(found for found in catalog.families() if found.identifier == "gold-silver-crystal")
        terrains = WildTerrains(CACHE)
        regions = {found.identifier: terrains.region(family, found.identifier) for found in catalog.maps(family)}
    finally:
        catalog.close()
    assert set(regions.values()) == {"johto", "kanto"}
    assert (regions["route-29"], regions["union-cave-1f"], regions["route-1"]) == ("johto", "johto", "kanto")
    # La Route Victoire et le Mont Argenté sont rangés en Johto, comme RegionCheck le fait pour leurs repères.
    assert (regions["victory-road"], regions["silver-cave-room-1"]) == ("johto", "johto")


class LocalTerrains:
    def rejected_versions(
        self, _family: Family, _identifier: str, _kind: str, _point: tuple[int, int]
    ) -> tuple[str, ...]:
        return ("Rouge/Bleu",)

    def kinds(self, _family: Family, _identifier: str) -> frozenset[str]:
        return frozenset({"grass"})

    def points(self, _family: Family, _identifier: str, _kind: str) -> frozenset[tuple[int, int]]:
        return GENERATED


def test_save_only_writes_csv(tmp_path: Path) -> None:
    family = Family(KEY.family, "Rouge, Bleu et Jaune", ("red-blue", "yellow"))
    session = SpotSession({})
    session.clear(KEY, GENERATED)
    path = tmp_path / "map_spots.csv"
    save_spots(session, [family], LocalTerrains(), path)
    assert read_spots(path) == {KEY: frozenset()}
    assert not session.has_changes
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_points_keep_file_and_pending_changes(tmp_path: Path) -> None:
    family = Family(KEY.family, "Rouge, Bleu et Jaune", ("red-blue", "yellow"))
    session = SpotSession({})
    session.toggle(KEY, GENERATED, (488, 456), never)
    path = tmp_path / "map_spots.csv"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(ValueError, match="rencontres sauvages dans Rouge/Bleu"):
        save_spots(session, [family], LocalTerrains(), path)
    assert path.read_text(encoding="utf-8") == "original"
    assert session.has_changes


@pytest.mark.usefixtures("source_cache_ready")
def test_dark_cave_points_are_rejected_locally() -> None:
    terrains = WildTerrains(CACHE)
    family = Family("gold-silver-crystal", "Or, Argent et Cristal", ("gold-silver", "crystal"))
    valid = terrains.points(family, "dark-cave-violet-entrance", "floor")
    assert valid
    assert not valid & {(488, 456), (504, 312), (504, 376)}


@pytest.mark.usefixtures("source_cache_ready")
def test_floor_reached_with_surf_is_valid_in_all_versions() -> None:
    terrains = WildTerrains(CACHE)
    family = Family("gold-silver-crystal", "Or, Argent et Cristal", ("gold-silver", "crystal"))
    assert {(56, 40), (56, 104), (152, 72), (184, 104)} <= terrains.points(family, "slowpoke-well-b2f", "floor")
    assert {(40, 376), (56, 280), (216, 360), (248, 264), (264, 72), (264, 104)} <= terrains.points(
        family, "union-cave-b2f", "floor"
    )


@pytest.mark.usefixtures("source_cache_ready")
def test_changed_crystal_map_names_the_version_rejecting_the_point() -> None:
    terrains = WildTerrains(CACHE)
    family = Family("gold-silver-crystal", "Or, Argent et Cristal", ("gold-silver", "crystal"))
    assert terrains.rejected_versions(family, "mount-mortar-2f-inside", "water", (216, 152)) == ("Cristal",)
    session = SpotSession({TerrainKey(family.identifier, "mount-mortar-2f-inside", "water"): frozenset({(216, 152)})})
    from spot_editor.validation import spot_errors

    [error] = spot_errors(session, [family], terrains)
    assert "dans Cristal" in error.message


@pytest.mark.usefixtures("source_cache_ready")
def test_gold_silver_only_point_is_not_validated_against_crystal() -> None:
    from spot_editor.validation import spot_errors

    terrains = WildTerrains(CACHE)
    family = Family("gold-silver-crystal", "Or, Argent et Cristal", ("gold-silver", "crystal"))
    key = TerrainKey(family.identifier, "mount-mortar-2f-inside", "water", "gold-silver")
    assert spot_errors(SpotSession({key: frozenset({(216, 152)})}), [family], terrains) == []
