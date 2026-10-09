"""PokéAPI de Rouge Feu et Vert Feuille : obtention, noms et zones propres au remake."""

import csv
from pathlib import Path

import pytest

from pokemaps_data import validate
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import EXTERNAL_EVENT_AREAS, EXTERNAL_EVENT_NOTE
from pokemaps_data.sources import DATA_DIR, pret_dir
from pokemaps_data.validate import _check_obtainable, _obtainable, _transfer_only

from .conftest import CACHE
from .test_gen3_pokemon import _pokemon_database


def test_remake_transfer_list_is_complete(gen3_builder: DatabaseBuilder, tmp_path: Path) -> None:
    connection = _pokemon_database(gen3_builder, tmp_path / "remake.db")
    try:
        allowed = _transfer_only(connection)["firered-leafgreen"]
        obtainable = _obtainable(connection, 3, (7,))
        # Exclusivités des deux versions, bébés issus d'espèces présentes et trois errants : pas de transfert externe.
        assert {23, 27, 37, 58, 123, 127, 161, 172, 175, 238, 239, 240, 243, 244, 245, 298, 360} <= obtainable
        assert not allowed & obtainable
        assert {152, 155, 158, 179, 190, 196, 197, 204, 213, 216, 228, 234, 235, 249, 250, 252, 384} <= allowed
        assert _check_obtainable(connection) == []
    finally:
        connection.close()


def test_missing_or_stale_remake_transfer_is_reported(
    gen3_builder: DatabaseBuilder, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with (DATA_DIR / "transfer_only.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows = [r for r in rows if (r["version_group"], r["pokemon"]) != ("firered-leafgreen", "treecko")]
    rows.append({"version_group": "firered-leafgreen", "pokemon": "sentret", "reason": "ligne devenue inutile"})
    with (tmp_path / "transfer_only.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["version_group", "pokemon", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(validate, "DATA_DIR", tmp_path)
    connection = _pokemon_database(gen3_builder, tmp_path / "remake.db")
    try:
        errors = _check_obtainable(connection)
        assert "Branche firered-leafgreen : Pokémon impossibles à obtenir : [252]" in errors
        assert "transfer_only.csv : Pokémon obtenables dans la branche firered-leafgreen : [161]" in errors
    finally:
        connection.close()


def test_altering_cave_event_tables_do_not_count_as_obtainable(gen3_builder: DatabaseBuilder) -> None:
    locations = gen3_builder.locations
    groups = [
        g
        for g in gen3_builder.encounters.encounter_groups
        if locations.area_locations[g.location_area_id] == "kanto-altering-cave"
    ]
    normal = [g for g in groups if locations.area_keys[g.location_area_id] not in EXTERNAL_EVENT_AREAS]
    event = [g for g in groups if locations.area_keys[g.location_area_id] in EXTERNAL_EVENT_AREAS]
    assert {g.pokemon_id for g in normal} == {41}
    assert normal and all(EXTERNAL_EVENT_NOTE not in g.notes for g in normal)
    assert {g.pokemon_id for g in event} == {179, 190, 204, 213, 216, 228, 234, 235}
    assert all(EXTERNAL_EVENT_NOTE in g.notes for g in event)
    # Le moteur ne change la variable que par une distribution externe ; le nouveau jeu l'initialise à zéro.
    root = pret_dir(CACHE, "pokefirered")
    source = (root / "src/event_data.c").read_text(encoding="utf-8")
    assert "VarSet(VAR_ALTERING_CAVE_WILD_SET, 0);" in source


def test_remake_places_have_readable_french_names(gen3_builder: DatabaseBuilder) -> None:
    locations = gen3_builder.locations
    used = {g.location_area_id for g in gen3_builder.encounters.encounter_groups if g.version_id in (10, 11)}
    areas = {locations.area_keys[r[0]]: r[3] for r in locations.location_area_table(used)}
    places = {r[1]: r[2] for r in locations.location_rows(used)}
    assert areas["rock-tunnel/1f"] == "Grotte (RdC)"
    assert areas["rock-tunnel/remake-b1f"] == "Grotte (1er sous-sol)"
    assert areas["pokemon-tower/7f"] == "Tour Pokémon (6e étage)"
    assert areas["mt-ember/b1f"] == "Mont Braise (1er sous-sol)"
    assert areas["kanto-pokecenter"] == "Centre Pokémon (Kanto)"
    assert areas["five-isle-meadow"] == "Pré Île 5"
    assert places["outcast-island"] == "Île du Lointain"
    assert places["one-island"] == "Île 1"
    assert places["monean-chamber"] == "Chambre Anemune"
    assert all(name != name.lower() for name in (*areas.values(), *places.values()))
    assert not any(mark in name for name in (*areas.values(), *places.values()) for mark in ("ét.", " s-sol", "Ile"))


def test_remake_rock_tunnel_encounters_and_rates_follow_the_correct_floor(gen3_builder: DatabaseBuilder) -> None:
    tables = gen3_builder.encounters
    source = gen3_builder.locations.area_ids["rock-tunnel/b1f"]
    target = gen3_builder.locations.area_ids["rock-tunnel/remake-b1f"]
    groups = [g for g in tables.encounter_groups if g.version_id in (10, 11) and g.location_area_id == target]
    assert {g.pokemon_id for g in groups} == {41, 56, 66, 74, 75, 95}
    assert not any(g.version_id in (10, 11) and g.location_area_id == source for g in tables.encounter_groups)
    rates = tables.encounter_rate_table()
    assert any(version == 10 and area == target for version, area, _, _ in rates)
    assert not any(version in (10, 11) and area == source for version, area, _, _ in rates)
