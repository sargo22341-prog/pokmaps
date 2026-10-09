"""Terrains qui manquent d'emplacements : avertissements, et erreurs quand il n'y en a aucun."""

from dataclasses import replace

from pokemaps_data.map_spots import SPOT_KINDS, Point, TerrainKey
from spot_editor.catalog import EditorMap, EncounterLine, Family
from spot_editor.coverage import PlacementNeeds
from spot_editor.session import SpotSession

FAMILY = Family("red-blue-yellow", "Rouge, Bleu et Jaune", ("red-blue", "yellow"))
ROUTE = EditorMap(FAMILY.identifier, "route-1", "Route 1", "red-blue", (1,), "kanto", 0, 0, 320, 576)
ROUTE_YELLOW = replace(ROUTE, version_group="yellow", map_ids=(3,))
CAVE = EditorMap(FAMILY.identifier, "cave", "Grotte", "red-blue", (2,), "cave", 0, 0, 320, 320)
GRASS = TerrainKey(FAMILY.identifier, "route-1", "grass")
FLOOR = TerrainKey(FAMILY.identifier, "cave", "floor")


def walk(version: str, pokemon_id: int) -> EncounterLine:
    return EncounterLine(version, "walk", "Marche", pokemon_id, str(pokemon_id), 2, 5, 10.0)


class FakeCatalog:
    """Route 1 : trois Pokémon en Rouge, deux en Jaune, deux points d'herbe. Grotte : un Pokémon, aucun point."""

    def maps(self, family: Family) -> list[EditorMap]:
        return [ROUTE, CAVE] if family.version_groups == ("red-blue",) else [ROUTE_YELLOW]

    def encounters(self, editor_map: EditorMap) -> list[EncounterLine]:
        if editor_map == CAVE:
            return [walk("Rouge", 41)]
        if editor_map == ROUTE_YELLOW:
            return [walk("Jaune", 16), walk("Jaune", 19)]
        return [walk("Rouge", 16), walk("Rouge", 19), walk("Rouge", 21)]

    def generated_spots(self, editor_map: EditorMap) -> dict[str, frozenset[Point]]:
        points = {kind: frozenset[Point]() for kind in SPOT_KINDS}
        if editor_map.identifier == ROUTE.identifier:
            points["grass"] = frozenset({(8, 8), (56, 8)})
        return points


class FakeTerrains:
    def kinds(self, _family: Family, identifier: str) -> frozenset[str]:
        return frozenset({"floor"} if identifier == "cave" else {"grass"})


def needs() -> PlacementNeeds:
    return PlacementNeeds(FakeCatalog(), [FAMILY], FakeTerrains())  # type: ignore[arg-type]


def test_too_few_points_warn_and_no_point_blocks() -> None:
    error, warning = needs().shortfalls(SpotSession({}))
    # Une seule ligne pour la portée commune : celle du groupe qui manque le plus de place.
    assert (warning.key, warning.version_group, warning.points, warning.required) == (GRASS, "red-blue", 2, 3)
    assert not warning.blocking
    assert "1 visible(s) dans la liste seulement" in warning.label
    # La grotte n'a ni herbes ni point : le manque est signalé sur son sol.
    assert (error.key, error.points, error.blocking) == (FLOOR, 0, True)


def test_enough_points_clear_the_shortfall() -> None:
    session = SpotSession({GRASS: frozenset({(8, 8), (56, 8), (104, 8)}), FLOOR: frozenset({(8, 8)})})
    assert needs().shortfalls(session) == []


def test_group_override_is_reported_on_its_own_scope() -> None:
    yellow = TerrainKey(GRASS.family, GRASS.map_identifier, "grass", "yellow")
    session = SpotSession(
        {GRASS: frozenset({(8, 8), (56, 8), (104, 8)}), FLOOR: frozenset({(8, 8)}), yellow: frozenset()}
    )
    [error] = needs().shortfalls(session)
    assert (error.key, error.version_group, error.required, error.blocking) == (yellow, "yellow", 2, True)
