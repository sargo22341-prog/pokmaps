"""Contrats des parcours et objectifs HGSS, sans sources téléchargées."""

from copy import deepcopy
from pathlib import Path

import pytest

from pokemaps_data.objectives_hgss import _safari_species, _wild_species, close_collection
from pokemaps_data.pret_gen4_source import read_json
from pokemaps_data.preview_content_hgss import CONTRACT, _validate_target, recipe
from pokemaps_data.sources_characters_hgss import source_digest
from pokemaps_data.validate_content_hgss import validate_content

CATALOG = CONTRACT.with_name("contenus-hgss-catalogue.json")


def test_versioned_content_is_valid_and_current() -> None:
    content = read_json(CATALOG)
    proof = read_json(CONTRACT.with_name("contenus-hgss-preuve.json"))
    assert source_digest(CATALOG) == proof["catalog_sha256"]
    assert content["recipe"] == recipe()
    assert content["sources"] == read_json(CONTRACT)
    validate_content(content)
    assert all(
        str(item["values"][0]) in content["item_names_fr"]
        for guide in content["guides"]
        for item in guide["items"]
        if item["values"]
    )


@pytest.mark.parametrize("version", ["heartgold", "soulsilver"])
def test_starter_choices_never_merge_incompatible_families(version: str) -> None:
    objectives = [r for r in read_json(CATALOG)["objectives"] if r["version"] == version]
    assert len(objectives) == 27
    assert len({tuple(row["starters"].values()) for row in objectives}) == 27
    for row in objectives:
        national = set(row["national"])
        for starts in ((1, 4, 7), (152, 155, 158), (252, 255, 258)):
            chosen = national & set(starts)
            assert len(chosen) == 1
            for start in set(starts) - chosen:
                assert not national & set(range(start, start + 3))


def test_local_legend_fossils_and_external_evolutions() -> None:
    rows = read_json(CATALOG)["objectives"]
    hg = set(rows[0]["national"])
    ss = set(rows[27]["national"])
    assert {138, 139, 142, 347, 348, 380, 382} <= hg
    assert {140, 141, 142, 345, 346, 381, 383} <= ss
    assert not {140, 345, 381, 383, 384, 408, 410} & hg
    assert not {138, 347, 380, 382, 384, 408, 410} & ss
    assert not {65, 68, 464, 470, 471, 462, 476, 483, 484, 487, 493} & (hg | ss)
    assert {172, 175, 208} <= hg & ss


def test_collection_closure_respects_trade_requirements_and_ditto() -> None:
    evolutions = [dict(species=1, target=2, access="local"), dict(species=2, target=3, access="external_trade")]
    trades = [dict(requested=2, given=4, loan=False), dict(requested=5, given=6, loan=False)]
    assert close_collection({1}, evolutions, {4: 7}, trades) == {1, 2, 4}
    assert close_collection({1, 132}, evolutions, {4: 7}, trades) == {1, 2, 4, 7, 132}


def test_objectives_ignore_banks_attached_only_to_excluded_maps() -> None:
    data = dict(
        maps=[dict(header=2)],
        banks=[dict(bank=1, headers=[100]), dict(bank=2, headers=[2])],
        distributions=[
            dict(bank=bank, method="walk", version="heartgold", slots=[dict(species=bank)]) for bank in (1, 2)
        ],
        headbutt=[],
        special_wild=dict(contest=[], safari=[]),
    )
    assert _wild_species(data, "heartgold") == {2}


@pytest.mark.parametrize("defect", ["cycle", "unknown_place", "external", "accessory", "unexplained"])
def test_content_rejects_broken_links_and_objectives(defect: str) -> None:
    data = deepcopy(read_json(CATALOG))
    if defect == "cycle":
        data["guides"][0]["requires"] = [data["guides"][1]["id"]]
    elif defect == "unknown_place":
        data["guides"][0]["places"][0]["header"] = 99999
    elif defect == "external":
        objective = data["objectives"][0]
        objective["national"].append(384)
        objective["excluded"].remove(384)
    elif defect == "accessory":
        data["activities"]["pokewalker"]["courses"][0]["ordinary_objective"] = True
    elif defect == "unexplained":
        data["objectives"][0]["exclusions"][0]["reason_fr"] = ""
    with pytest.raises(ValueError, match="HGSS"):
        validate_content(data)


def test_safari_objective_excludes_impossible_block_requirements() -> None:
    mon = dict(species="SPECIES_TEST", level=10)
    bonus = dict(
        morn=dict(species="SPECIES_BONUS", level=20),
        conditions=[dict(object_type="SAFARI_ZONE_OBJECT_TYPE_PLAINS", count=211)],
    )
    table = dict(mons=dict(morn=[mon] * 10), bonus_mons=[bonus])
    assert _safari_species(table, "morn", {"SPECIES_TEST": 1, "SPECIES_BONUS": 2}) == {1}
    bonus["conditions"][0]["count"] = 210
    assert _safari_species(table, "morn", {"SPECIES_TEST": 1, "SPECIES_BONUS": 2}) == {1, 2}


def test_guides_use_distinct_legends_and_reach_red() -> None:
    guides = read_json(CATALOG)["guides"]
    legends = {r["version"]: r for r in guides if r["id"] == "legende"}
    assert "Ho-Oh" in legends["heartgold"]["title_fr"]
    assert "Lugia" in legends["soulsilver"]["title_fr"]
    assert all(row["actors"] and row["sources"] for row in legends.values())
    assert len([r for r in guides if r["id"] == "red"]) == 2
    assert any(row["items"] for row in guides if row["id"] == "sandra")
    ecorcia = next(row for row in guides if row["id"] == "ecorcia")
    assert any(item["quantity_rule"] for item in ecorcia["items"] if not item["values"])


def test_radio_quest_links_only_the_wing_of_the_selected_cartouche() -> None:
    rows = [row for row in read_json(CATALOG)["guides"] if row["id"] == "radio"]
    for row in rows:
        items = {item["values"][0] for item in row["items"] if item["values"]}
        assert items & {482, 483} == ({483} if row["version"] == "heartgold" else {482})


def test_content_preview_cannot_replace_source_files(tmp_path: Path) -> None:
    cache = tmp_path / "sources"
    with pytest.raises(ValueError, match="séparés"):
        _validate_target(cache, cache)
