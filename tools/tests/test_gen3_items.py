"""Objets GBA : pas de perte de quantité, de drapeau ni de variante de version."""

from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.maps_items_gen3 import _identifier
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_items import map_items, read_map_items
from pokemaps_data.pret_gen3_maps import Gen3Event, Gen3Layout, Gen3Map
from pokemaps_data.pret_gen3_offers import ScriptOffers, script_offers
from pokemaps_data.pret_gen3_scripts import Gen3Scripts, parse_scripts
from pokemaps_data.sources import pret_dir


class _Reader:
    def __init__(self, text: str) -> None:
        self.scripts = Gen3Scripts(
            parse_scripts(text, "test.inc"),
            {"ITEM_NONE": 0, "ITEM_POTION": 13, "ITEM_ANTIDOTE": 14, "FLAG_ITEM": 10},
        )

    def read(self, label: str) -> ScriptOffers:
        if label == "NULL":
            return ScriptOffers((), (), (), ())
        return script_offers(self.scripts, label)


def _map(*, script: str = "Gift", hidden: bool = False, **fields: str | int | bool) -> Gen3Map:
    layout = Gen3Layout("LAYOUT_TEST", 4, 4, "PRIMARY", "SECONDARY", (0,) * 16, 2, 2, (0,) * 4)
    values = {"script": script, "graphics_id": "OBJ_EVENT_GFX_ITEM_BALL", "flag": "FLAG_ITEM"} | fields
    event = Gen3Event("hidden_item" if hidden else "object", 2, 3, 1, tuple(values.items()))
    return Gen3Map(
        "MAP_TEST",
        "Test",
        1,
        0,
        0,
        layout,
        "MAP_TYPE_ROUTE",
        "MAPSEC_TEST",
        (),
        (),
        () if hidden else (event,),
        (),
        (event,) if hidden else (),
        None,
        None,
        (),
    )


def test_ball_keeps_removal_flag_quantity_version_and_position() -> None:
    item = map_items(_map(), "ruby", _Reader("Gift:\ngiveitem ITEM_POTION, 2\nend"))[0]
    assert (item.item, item.quantity, item.removal_flag, item.version) == ("ITEM_POTION", 2, "FLAG_ITEM", "ruby")
    assert (item.x, item.y, item.elevation, item.script) == (2, 3, 1, "Gift")


def test_hidden_items_keep_quantity_and_underfoot_attribute() -> None:
    item = map_items(_map(hidden=True, item="ITEM_POTION", quantity=3, underfoot=True), "firered", _Reader(""))[0]
    assert (item.kind, item.quantity, item.underfoot, item.script) == ("hidden_item", 3, True, None)


def test_hidden_coins_are_not_an_item_named_none() -> None:
    reader = _Reader("EventScript_TryPickUpHiddenCoins:\nend")
    item = map_items(_map(hidden=True, item="ITEM_NONE", quantity=100), "firered", reader)[0]
    assert (item.kind, item.quantity) == ("hidden_coins", 100)


def test_none_item_without_coin_engine_stops_export() -> None:
    with pytest.raises(ValueError, match="jetons cachés"):
        map_items(_map(hidden=True, item="ITEM_NONE", quantity=10), "ruby", _Reader(""))


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"flag": "0"}, "drapeau"),
        ({"flag": "FLAG_UNKNOWN"}, "drapeau"),
        ({"item": "ITEM_UNKNOWN"}, "inconnu"),
        ({"quantity": 0}, "quantité"),
        ({"underfoot": "TRUE"}, "underfoot"),
    ],
)
def test_invalid_hidden_item_stops_export(fields: dict[str, str | int | bool], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        map_items(_map(hidden=True, **({"item": "ITEM_POTION"} | fields)), "ruby", _Reader(""))


def test_outside_position_stops_export() -> None:
    current = _map(hidden=True, item="ITEM_POTION")
    current = replace(current, bg_events=(replace(current.bg_events[0], x=4),))
    with pytest.raises(ValueError, match="hors carte"):
        map_items(current, "ruby", _Reader(""))


@pytest.mark.parametrize(
    "text, message",
    [
        ("Gift:\ngiveitem VAR_REWARD\nend", "moteur"),
        ("Gift:\nspecial UnknownEffect\nend", "appels C"),
        ("Gift:\ngiveitem ITEM_POTION\ngiveitem ITEM_ANTIDOTE\nend", "ambigu"),
        ("Gift:\ngoto_if_set FLAG_ITEM, Done\ngiveitem ITEM_POTION\nDone:\nend", "conditionnel"),
    ],
)
def test_ambiguous_or_unreviewed_ball_stops_export(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        map_items(_map(), "ruby", _Reader(text))


@pytest.mark.parametrize(
    "text",
    [
        "Gift:\ngivemon SPECIES_BELDUM, 5\nend",
        "Gift:\nsetwildbattle SPECIES_ELECTRODE, 30, ITEM_NONE\nend",
        "Gift:\nmsgbox RivalText\nend",
    ],
)
def test_pokemon_and_decorative_balls_are_not_pickup_items(text: str) -> None:
    assert not map_items(_map(), "ruby", _Reader(text))


def test_null_script_ball_is_decorative() -> None:
    assert not map_items(_map(script="NULL"), "ruby", _Reader(""))


def test_named_machine_alias_uses_numbered_pokeapi_identifier() -> None:
    constants = {"ITEM_TM37": 325, "ITEM_TM_SANDSTORM": 325}
    assert _identifier("ITEM_TM_SANDSTORM", constants) == "tm37"
    assert _identifier("ITEM_PARLYZ_HEAL", {"ITEM_PARLYZ_HEAL": 18}) == "paralyze-heal"


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_pinned_fixed_items_are_read_for_every_version(source_cache_ready: None, game: Game) -> None:
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        items = read_map_items(repo, version)
        assert len(items) > 200
        assert {item.kind for item in items} >= {"item", "hidden_item"}
        assert all(item.version == version and item.removal_flag.startswith("FLAG_") for item in items)
        if repo.remake:
            coins = [item for item in items if item.kind == "hidden_coins"]
            assert len(coins) == 12
            assert sum(item.quantity for item in coins) == 260
        if not repo.ruby and not repo.remake:
            sandstorm = next(item for item in items if item.item == "ITEM_TM_SANDSTORM")
            assert sandstorm.map_const == "MAP_ROUTE111"
            assert _identifier(sandstorm.item, repo.offers[version].scripts.constants) == "tm37"
