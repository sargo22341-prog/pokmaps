"""Recette des tables HGSS et des profils propres aux deux cartouches depuis les sources épinglées."""

import json
from pathlib import Path

import pytest

from pokemaps_data.catalog_pokemon_hgss import pokemon_catalog
from pokemaps_data.compare_pokemon_hgss import compare_pokemon
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pokemon_forms_hgss import build_forms
from pokemaps_data.pret_hgss_pokemon import read_hgss_pokemon
from pokemaps_data.preview_pokemon_hgss import validate_comparison, validate_sources
from pokemaps_data.sources import DATA_DIR, POKEAPI_COMMIT

_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.pipeline
def test_pinned_hgss_pokemon_and_cartouche_profiles() -> None:
    root = _ROOT / "tools/.cache/hgss-qualification"
    api_root = _ROOT / "tools/.cache" / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    validate_sources(root, api_root)
    data = read_hgss_pokemon(root)
    api = PokeApi(api_root)
    rules = json.loads((DATA_DIR / "hgss_pokemon_rules.json").read_text("utf-8"))
    report = compare_pokemon(data, api)
    validate_comparison(report, rules)
    assert report["learnset_differences"] == report["stat_differences"] == []
    assert data.machines[96] == 250  # Siphon, et non Anti-Brume de Sinnoh.
    assert data.personal[35]["types"] == ["TYPE_NORMAL", "TYPE_NORMAL"]
    assert data.personal[94]["abilities"] == ["ABILITY_LEVITATE", "ABILITY_NONE"]
    assert data.personal[382]["catchRate"] == 5
    forms = build_forms(data, rules)
    for version in ("heartgold", "soulsilver"):
        selected = {row["identifier"]: row for row in forms if row["version"] == version}
        assert len(selected) == 47
        heat = selected["rotom-heat"]
        assert heat["personal"]["types"] == ["TYPE_ELECTRIC", "TYPE_GHOST"]
        assert heat["personal"]["spatk"] == 105
        assert selected["deoxys-attack"]["personal"]["atk"] == 180
        assert selected["shaymin-sky"]["personal"]["speed"] == 127
        assert "TUTOR_EARTH_POWER" in selected["wormadam-sandy"]["tutor_moves"]
        assert "TUTOR_HEADBUTT" not in selected["wormadam-sandy"]["tutor_moves"]
    catalog = pokemon_catalog(data, api, rules, forms)
    assert [r["id"] for r in catalog["versions"]] == [15, 16]
    assert len(catalog["pokemon"]) == 493 and len(catalog["moves"]) == 467
    assert {e["target"] for e in catalog["evolutions"] if e["access"] == "other-game"} == {
        "SPECIES_MAGNEZONE",
        "SPECIES_PROBOPASS",
        "SPECIES_LEAFEON",
        "SPECIES_GLACEON",
    }
    assert catalog["special_forms"][0]["evolves"] is False
    assert catalog["special_forms"][0]["tradeable"] is False
    assert all(r["version_group_id"] == "10" for r in catalog["supplementary_moves"]["rows"])


@pytest.mark.pipeline
def test_unown_groups_are_read_from_hgss_engine() -> None:
    path = _ROOT / "tools/.cache/hgss-qualification/src/field/encounter_check.c"
    text = path.read_text(encoding="utf-8")
    rules = json.loads((DATA_DIR / "hgss_pokemon_rules.json").read_text("utf-8"))["unown"]
    for name, letters in rules["puzzles"].items():
        block = text.split(f"sUnlockedUnown_{name}[] = {{", 1)[1].split("};", 1)[0]
        assert [line.strip().removeprefix("UNOWN_").rstrip(",") for line in block.splitlines() if "UNOWN_" in line] == (
            list(letters)
        )
    assert "UNOWN_EXCLAMATION_MARK" in text and "UNOWN_QUESTION_MARK" in text
    assert "if (encounterGen->isSinjohMap)" in text
    map_header = (_ROOT / "tools/.cache/hgss-qualification/src/map_header.c").read_text("utf-8")
    body = map_header.split("MapHeader_GetMapEvolutionMethod(u32 mapId) {", 1)[1].split("}", 1)[0]
    assert "return EVO_NONE;" in body
