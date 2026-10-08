"""Règles de l'éditeur d'emplacements, sans fenêtre : catalogue, état d'édition et contrôles."""

import queue
import sys
from pathlib import Path

from pokemaps_data.map_spots import TerrainKey
from spot_editor.catalog import EditorCatalog, EditorMap, EncounterLine, required_spots, used_by_app
from spot_editor.session import SpotSession, Toggle
from spot_editor.terrain import WildTerrains
from spot_editor.validation import Step, StepEvent, StepState, run_steps, validation_plan

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


def test_validation_stops_at_the_first_failing_step(tmp_path: Path) -> None:
    events: queue.Queue[StepEvent] = queue.Queue()
    steps = (
        Step("ok", tmp_path, (sys.executable, "-c", "pass")),
        Step("ko", tmp_path, (sys.executable, "-c", "import sys; print('détail'); sys.exit(3)")),
        Step("jamais", tmp_path, (sys.executable, "-c", "pass")),
    )
    run_steps(steps, events)
    received = [events.get_nowait() for _ in range(events.qsize())]
    assert [(event.state, event.label) for event in received] == [
        (StepState.PROGRESS, "ok"),
        (StepState.PROGRESS, "ko"),
        (StepState.FAILURE, "ko"),
    ]
    assert "détail" in received[-1].output


def test_validation_reports_success(tmp_path: Path) -> None:
    events: queue.Queue[StepEvent] = queue.Queue()
    run_steps((Step("ok", tmp_path, (sys.executable, "-c", "pass")),), events)
    assert [events.get_nowait().state for _ in range(events.qsize())] == [StepState.PROGRESS, StepState.SUCCESS]


def test_editor_runs_both_asset_and_pipeline_tests(tmp_path: Path) -> None:
    commands = [step.command for step in validation_plan(tmp_path)]
    assert (sys.executable, "-m", "pytest", "-q") in commands
    assert (sys.executable, "-m", "pytest", "-q", "-m", "pipeline") in commands
