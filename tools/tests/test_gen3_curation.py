"""Corrections GBA : provenance, conditions et conservation des dresseurs."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data import character_curation_gen3
from pokemaps_data.character_curation_gen3 import Gen3Curation, OfferResolution, character_key, read_gen3_curation
from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_conditions import ScriptRequirement
from pokemaps_data.pret_gen3_maps import Gen3Event
from pokemaps_data.pret_gen3_offers import Gen3Offer, ScriptOffers
from pokemaps_data.pret_gen3_script_values import script_constants
from pokemaps_data.sources import pret_dir
from pokemaps_data.story_events import StoryEvents, read_story_events


def _result() -> ScriptOffers:
    offer = Gen3Offer(
        "gift_item",
        item="VAR_REWARD",
        quantity="4",
        source="test.inc:5",
        paths=(frozenset({ScriptRequirement("FLAG_DONE", "eq", "FALSE")}),),
    )
    return ScriptOffers((offer,), ("TRAINER_TEST",), ("FLAG_DONE",), ("ComputeReward",))


def _curation() -> Gen3Curation:
    return Gen3Curation(
        (),
        tuple(
            OfferResolution(frozenset({"pokeemerald"}), "Map:1", "VAR_REWARD", item, "table C relue")
            for item in ("ITEM_POTION", "ITEM_ANTIDOTE")
        ),
    )


def test_resolution_keeps_each_path_quantity_source_and_trainer() -> None:
    original = _result()
    result = _curation().apply("pokeemerald", "Map:1", original)
    assert result.offers == tuple(replace(original.offers[0], item=item) for item in ("ITEM_POTION", "ITEM_ANTIDOTE"))
    assert (result.trainers, result.flags, result.specials) == (original.trainers, original.flags, original.specials)
    assert not result.unresolved
    with pytest.raises(ValueError, match="appels C à relire"):
        result.require_resolved("Map:1")


@pytest.mark.parametrize("repo,key", [("pokeruby", "Map:1"), ("pokeemerald", "Other:1")])
def test_resolution_never_leaks_to_another_repo_or_object(repo: str, key: str) -> None:
    assert _curation().apply(repo, key, _result()) == _result()


def test_stale_resolution_is_rejected() -> None:
    with pytest.raises(ValueError, match="résolution inutilisée"):
        _curation().apply("pokeemerald", "Map:1", replace(_result(), offers=()))


def test_shared_script_resolution_preserves_dynamic_quantity_and_source_selection() -> None:
    row = replace(_curation().resolutions[0], key="@script:Shared", quantity="1", source="test.inc:5")
    original = replace(_result(), offers=(replace(_result().offers[0], quantity="VAR_QUANTITY"),))
    curation = Gen3Curation((), (row,))
    assert curation.apply("pokeemerald", "Any:1", original, "Other") == original
    result = curation.apply("pokeemerald", "Any:1", original, "Shared")
    assert result.offers[0].quantity == "1"
    assert result.offers[0].source == "test.inc:5"
    with pytest.raises(ValueError, match="quantité du script modifiée"):
        curation.apply("pokeemerald", "Any:1", _result(), "Shared")


def test_custom_quiz_reward_is_explicit_and_keeps_the_script_paths() -> None:
    row = replace(
        _curation().resolutions[0],
        kind="gift_custom_item",
        item=None,
        conditions=("Lot choisi par l'auteur du quiz",),
    )
    result = Gen3Curation((), (row,)).apply("pokeemerald", "Map:1", _result())
    offer = result.offers[0]
    assert offer.kind == "gift_custom_item" and offer.item is None
    assert offer.conditions == row.conditions
    assert offer.paths == _result().offers[0].paths
    assert not result.unresolved


def test_source_selection_does_not_mix_received_and_sent_news_rewards() -> None:
    row = replace(_curation().resolutions[0], source="test.inc:5")
    other = replace(_result().offers[0], source="test.inc:8")
    result = Gen3Curation((), (row,)).apply(
        "pokeemerald", "Map:1", replace(_result(), offers=(_result().offers[0], other))
    )
    assert result.offers[0].item == "ITEM_POTION"
    assert result.offers[1] == other


def test_variable_tutor_keeps_paths_price_eligible_species_and_individual_flag() -> None:
    row = replace(
        _curation().resolutions[0],
        kind="move_tutor",
        item=None,
        move="MOVE_FRENZY_PLANT",
        price=24,
        pokemon="SPECIES_VENUSAUR",
        required_flag="FLAG_TUTOR_FRENZY_PLANT",
        conditions=("Amitié maximale",),
    )
    original = replace(
        _result(), offers=(replace(_result().offers[0], kind="move_tutor", item=None, move="VAR_REWARD"),)
    )
    result = Gen3Curation((), (row,)).apply("pokeemerald", "Map:1", original)
    offer = result.offers[0]
    assert offer.move == "MOVE_FRENZY_PLANT" and offer.eligible_pokemon == "SPECIES_VENUSAUR"
    assert offer.price == 24 and offer.currency == "battle_points"
    assert offer.conditions == row.conditions
    assert offer.paths == (original.offers[0].paths[0] | {ScriptRequirement("FLAG_TUTOR_FRENZY_PLANT", "eq", "FALSE")},)
    assert result.trainers == original.trainers


def test_resolution_cannot_add_a_contradictory_flag() -> None:
    row = replace(_curation().resolutions[0], required_flag="FLAG_TUTOR_USED")
    offer = replace(_result().offers[0], paths=(frozenset({ScriptRequirement("FLAG_TUTOR_USED", "eq", "TRUE")}),))
    with pytest.raises(ValueError, match="drapeau incompatible"):
        Gen3Curation((), (row,)).apply("pokeemerald", "Map:1", replace(_result(), offers=(offer,)))


def test_character_key_uses_map_and_local_id_with_index_fallback() -> None:
    event = Gen3Event("object", 1, 2, 0, (("local_id", "LOCALID_TEST"),))
    assert character_key("Map", event, 3) == "Map:LOCALID_TEST"
    assert character_key("Other", event, 3) == "Other:LOCALID_TEST"
    assert character_key("Map", replace(event, fields=()), 3) == "Map:3"


def test_empty_header_guard_does_not_swallow_the_first_flag(tmp_path: Path) -> None:
    directory = tmp_path / "include/constants"
    directory.mkdir(parents=True)
    (directory / "flags.h").write_text(
        "#ifndef GUARD_FLAGS\n#define GUARD_FLAGS\n\n#define FLAG_TEMP_1 0x1\n#define FLAG_TEMP_2 0x2\n#endif\n",
        encoding="utf-8",
    )
    constants = script_constants(tmp_path)
    assert constants["FLAG_TEMP_1"] == 1 and constants["FLAG_TEMP_2"] == 2
    assert "GUARD_FLAGS" not in constants


def test_duplicate_is_scoped_to_its_family() -> None:
    curation = Gen3Curation((("firered-leafgreen", "Map:1"),), ())
    assert curation.is_duplicate("firered-leafgreen", "Map:1")
    assert not curation.is_duplicate("ruby-sapphire-emerald", "Map:1")


@pytest.mark.parametrize(
    "column,value",
    [
        ("repos", "pokered"),
        ("text", "Script"),
        ("kind", "sale"),
        ("item", "UNKNOWN"),
        ("expression", ""),
        ("reason", ""),
        ("quantity", "2"),
        ("source", "bad source"),
        ("price", "101"),
        ("pokemon", "NOT_A_SPECIES"),
        ("required_flag", "NOT_A_FLAG"),
        ("move", "MOVE_TACKLE"),
    ],
)
def test_invalid_resolution_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    column: str,
    value: str,
) -> None:
    import csv

    row = dict(
        repos="pokeemerald",
        text="Map:1",
        action="resolve",
        kind="gift_item",
        item="ITEM_POTION",
        wanted_item="",
        quantity="",
        price="",
        pokemon="",
        expression="VAR_REWARD",
        reason="source C",
    )
    row[column] = value
    (tmp_path / "npc_duplicates.csv").write_text("family,text,reason\n", encoding="utf-8")
    with (tmp_path / "npc_offers.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, list(row))
        writer.writeheader()
        writer.writerow(row)
    monkeypatch.setattr(character_curation_gen3, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match=r"npc_offers\.csv"):
        read_gen3_curation()


def test_pinned_curation_is_used_and_keeps_trainer_references(source_cache_ready: None) -> None:
    curation = read_gen3_curation()
    story = read_story_events()
    used_duplicates: set[tuple[str, str]] = set()
    used_resolutions: set[OfferResolution] = set()
    for game in GEN3_GAMES:
        repo = Gen3PretRepo(
            pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions
        )
        _check_engine_rewards(repo, game.pret_repo, curation)
        for current in repo.maps.values():
            for index, event in enumerate(current.objects, 1):
                key = character_key(current.label, event, index)
                duplicate = curation.is_duplicate(game.map_family, key)
                if event.kind == "clone":
                    continue
                rows = curation.rows_for(game.pret_repo, key, str(event.value("script")))
                for version, _ in game.pret_versions:
                    reader = repo.offers[version]
                    result = reader.read_curated_object(current.label, event, index, game.map_family)
                    if duplicate:
                        used_duplicates.add((game.map_family, key))
                        assert not result.offers and not result.trainers
                        assert not reader.read_object(event).trainers
                    else:
                        original = reader.read_object(event)
                        assert not result.unresolved
                        assert result.trainers == original.trainers
                        assert result.flags == original.flags and result.specials == original.specials
                        assert set(result.trainers) <= repo.trainers[version].keys()
                        used_resolutions.update(rows)
                        if rows:
                            _check_story_paths(story, reader.scripts.constants, game.pret_repo, key, result)
    assert used_duplicates == set(curation.duplicates)
    assert used_resolutions == set(curation.resolutions)


def _check_story_paths(
    story: StoryEvents, constants: dict[str, int], repo: str, key: str, result: ScriptOffers
) -> None:
    for offer in result.offers:
        for path in offer.paths:
            numeric = frozenset(
                replace(req, value=str(constants.get(req.value, req.value))) if req.subject.startswith("VAR_") else req
                for req in path
            )
            if numeric:
                assert story.script_phrases(repo, numeric, key)


def _check_engine_rewards(repo: Gen3PretRepo, name: str, curation: Gen3Curation) -> None:
    items = {
        row.item
        for row in curation.resolutions
        if name in row.repos
        and ("LOTTERY" in row.key or "LOTTERY" in row.expression or "POKELOT" in row.expression or "SELPHY" in row.key)
    }
    if name in {"pokeruby", "pokeemerald"}:
        text = (repo.root / "src/lottery_corner.c").read_text(encoding="utf-8")
        table = text.split("sLotteryPrizes[]", 1)[1].split("};", 1)[0]
        assert items == set(re.findall(r"ITEM_\w+", table))
    else:
        text = (repo.root / "src/field_specials.c").read_text(encoding="utf-8")
        table = text.split("sResortGorgeousDeluxeRewards[]", 1)[1].split("};", 1)[0]
        assert "return ITEM_LUXURY_BALL;" in text
        assert items == set(re.findall(r"ITEM_\w+", table)) | {"ITEM_LUXURY_BALL"}
