"""Scripts GBA : retours contextualisés, offres explicites et conditions contradictoires."""

from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_conditions import ScriptRequirement, script_states
from pokemaps_data.pret_gen3_offers import script_offers
from pokemaps_data.pret_gen3_script_effects import special_writes
from pokemaps_data.pret_gen3_script_values import number_value
from pokemaps_data.pret_gen3_scripts import Gen3Scripts, parse_scripts
from pokemaps_data.pret_gen3_source import conditional_text
from pokemaps_data.sources import pret_dir


def _scripts(text: str, constants: dict[str, int] | None = None) -> Gen3Scripts:
    return Gen3Scripts(parse_scripts(text, "test.inc"), constants or {})


def test_bit_shift_constants_are_bounded() -> None:
    assert number_value("(1 << 7)", {}) == 128
    assert number_value("(1 << 65535)", {}) is None
    assert number_value("(-1 << 2)", {}) is None


def test_calls_keep_each_item_in_its_own_context() -> None:
    scripts = _scripts(
        """Entry:
        setvar VAR_0x8000, ITEM_POTION
        call Give
        setvar VAR_0x8000, ITEM_ANTIDOTE
        call Give
        end
        Give:
        giveitem VAR_0x8000, 2
        return
        """
    )
    offers = script_offers(scripts, "Entry").offers
    assert [(offer.item, offer.quantity) for offer in offers] == [("ITEM_POTION", "2"), ("ITEM_ANTIDOTE", "2")]


def test_pokemon_egg_and_healing_keep_their_script_values() -> None:
    scripts = _scripts(
        "Entry:\nsetvar VAR_0x8000, SPECIES_BELDUM\ngivemon VAR_0x8000, 5, ITEM_ORAN_BERRY\n"
        "giveegg SPECIES_WYNAUT\nspecial HealPlayerParty\nend"
    )
    offers = script_offers(scripts, "Entry").offers
    assert [(offer.kind, offer.pokemon, offer.item, offer.quantity) for offer in offers] == [
        ("gift_pokemon", "SPECIES_BELDUM", "ITEM_ORAN_BERRY", "5"),
        ("gift_egg", "SPECIES_WYNAUT", None, "5"),
        ("heal", None, None, None),
    ]


def test_tutor_keeps_the_attack_selected_before_the_call() -> None:
    scripts = _scripts("Entry:\nsetvar VAR_0x8005, TUTOR_MOVE_ROLLOUT\nspecial TeachMoveTutorMove\nend")
    offer = script_offers(scripts, "Entry").offers[0]
    assert (offer.kind, offer.move) == ("move_tutor", "TUTOR_MOVE_ROLLOUT")


@pytest.mark.parametrize("amount", ["", ", 5", ", 5, MUS_LEVEL_UP"])
def test_remake_giveitem_message_keeps_item_and_quantity(amount: str) -> None:
    scripts = _scripts(f"Entry:\ngiveitem_msg ReceivedText, ITEM_POKE_BALL{amount}\nend")
    result = script_offers(scripts, "Entry")
    result.require_resolved("Entry")
    assert len(result.offers) == 1
    assert result.offers[0].item == "ITEM_POKE_BALL"
    assert result.offers[0].quantity == ("5" if amount else "1")


@pytest.mark.parametrize(
    "battle",
    [
        "trainerbattle_single TRAINER_TEST, Intro, Lose, Victory",
        "trainerbattle_double TRAINER_TEST, Intro, Lose, NeedTwo, Victory",
        "trainerbattle TRAINER_BATTLE_CONTINUE_SCRIPT, TRAINER_TEST, 0, Intro, Lose, Victory",
        "trainerbattle 2, TRAINER_TEST, 0, Intro, Lose, Victory",
        "trainerbattle 6, TRAINER_TEST, 0, Intro, Lose, NeedTwo, Victory",
    ],
)
def test_victory_scripts_are_followed_and_return_to_the_correct_dialogue(battle: str) -> None:
    scripts = _scripts(
        f"Entry:\n{battle}\ngiveitem ITEM_POTION\nend\nVictory:\ngiveitem ITEM_TM39\ngotopostbattlescript\n"
    )
    result = script_offers(scripts, "Entry")
    result.require_resolved("Entry")
    assert {offer.item for offer in result.offers} == {"ITEM_POTION", "ITEM_TM39"}


def test_victory_script_cannot_silently_disappear() -> None:
    scripts = _scripts("Entry:\ntrainerbattle_single TRAINER_TEST, Intro, Lose, Missing\nend")
    with pytest.raises(ValueError, match="Script GBA absent"):
        script_offers(scripts, "Entry")


@pytest.mark.parametrize(
    ("special", "kind"),
    [("DeleteMonMove", "move_deleter"), ("DisplayMoveTutorMenu", "move_relearner")],
)
def test_ruby_sapphire_move_services_are_recognized(special: str, kind: str) -> None:
    result = script_offers(_scripts(f"Entry:\nspecial {special}\nend"), "Entry")
    assert [offer.kind for offer in result.offers] == [kind]
    assert result.specials == (special,)


def test_flag_and_variable_conditions_follow_both_paths() -> None:
    scripts = _scripts(
        """Entry:
        goto_if_unset FLAG_SYS_GAME_CLEAR, Finished
        goto_if_ne VAR_STORY, 3, Finished
        giveitem ITEM_POTION
        Finished:
        end
        """
    )
    offer = script_offers(scripts, "Entry").offers[0]
    assert offer.paths == (
        frozenset({ScriptRequirement("FLAG_SYS_GAME_CLEAR", "ne", "FALSE"), ScriptRequirement("VAR_STORY", "eq", "3")}),
    )


def test_impossible_variable_interval_does_not_produce_a_gift() -> None:
    scripts = _scripts(
        """Entry:
        goto_if_lt VAR_STORY, 3, Finished
        goto_if_ge VAR_STORY, 2, Finished
        giveitem ITEM_POTION
        Finished:
        end
        """
    )
    assert not script_offers(scripts, "Entry").offers


def test_version_style_compare_and_goto_are_read() -> None:
    scripts = _scripts(
        """Entry:
        compare VAR_STORY, 3
        goto_if_eq Gift
        end
        Gift:
        giveitem ITEM_POTION
        end
        """
    )
    assert script_offers(scripts, "Entry").offers[0].paths == (frozenset({ScriptRequirement("VAR_STORY", "eq", "3")}),)


def test_shop_lists_keep_both_scenario_variants() -> None:
    scripts = _scripts(
        """Entry:
        goto_if_set FLAG_BADGE01_GET, Expanded
        pokemart Basic
        end
        Expanded:
        pokemart More
        end
        Basic:
        .2byte ITEM_POTION
        .2byte ITEM_NONE
        release
        end
        More:
        .2byte ITEM_POTION
        .2byte ITEM_SUPER_POTION
        pokemartlistend
        """
    )
    offers = script_offers(scripts, "Entry").offers
    assert [offer.item for offer in offers].count("ITEM_POTION") == 2
    assert next(offer for offer in offers if offer.item == "ITEM_SUPER_POTION").paths == (
        frozenset({ScriptRequirement("FLAG_BADGE01_GET", "eq", "TRUE")}),
    )


def test_random_berries_are_expanded_from_the_engine_range() -> None:
    scripts = _scripts(
        """Entry:
        random 2
        addvar VAR_RESULT, FIRST_BERRY_INDEX
        giveitem VAR_RESULT
        end
        """,
        {"FIRST_BERRY_INDEX": 133, "ITEM_CHERI_BERRY": 133, "ITEM_CHESTO_BERRY": 134},
    )
    result = script_offers(scripts, "Entry")
    assert {offer.item for offer in result.offers} == {"ITEM_CHERI_BERRY", "ITEM_CHESTO_BERRY"}
    result.require_resolved("Entry")


def test_c_computed_reward_cannot_be_exported_without_review() -> None:
    scripts = _scripts("Entry:\ngiveitem VAR_REWARD\nend")
    result = script_offers(scripts, "Entry")
    assert result.unresolved == result.offers
    with pytest.raises(ValueError, match="moteur à relire"):
        result.require_resolved("Entry")


def test_opaque_c_call_cannot_be_exported_as_an_empty_offer_list() -> None:
    result = script_offers(_scripts("Entry:\nspecial UnknownEffect\nend"), "Entry")
    assert result.specials == ("UnknownEffect",)
    with pytest.raises(ValueError, match="appels C à relire"):
        result.require_resolved("Entry")


@pytest.mark.parametrize("command", ["giveitem ITEM_POTION", "specialvar VAR_RESULT, UnknownResult"])
def test_engine_result_writes_do_not_reuse_a_prior_answer(command: str) -> None:
    scripts = _scripts(
        f"Entry:\nsetvar VAR_RESULT, 0\n{command}\ngoto_if_eq VAR_RESULT, 1, Gift\nend\n"
        "Gift:\ngiveitem ITEM_ANTIDOTE\nend"
    )
    assert any(offer.item == "ITEM_ANTIDOTE" for offer in script_offers(scripts, "Entry").offers)


@pytest.mark.parametrize("text", ["Entry:\ncall Missing", "Entry:\ncall Entry"])
def test_missing_script_and_recursive_calls_stop_reading(text: str) -> None:
    with pytest.raises(ValueError, match=r"absent|trop profonds"):
        script_states(_scripts(text), "Entry")


def test_duplicate_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="label répété"):
        parse_scripts("Entry:\nend\nEntry:\nend", "test.inc")


def test_assembler_endc_selects_the_correct_version(tmp_path: Path) -> None:
    path = tmp_path / "test.inc"
    path.write_text(".ifdef SAPPHIRE\nSAPPHIRE\n.else\nRUBY\n.endc\n", encoding="utf-8")
    assert conditional_text(path, frozenset({"SAPPHIRE"})).strip() == "SAPPHIRE"
    assert conditional_text(path, frozenset({"RUBY"})).strip() == "RUBY"


def test_constant_expressions_do_not_execute_python() -> None:
    assert number_value("(LAST - FIRST + 1)", {"LAST": 142, "FIRST": 133}) == 10
    assert number_value("LAST - (FIRST + 1)", {"LAST": 142, "FIRST": 133}) == 8
    assert number_value("__import__('os')", {}) is None


@pytest.mark.parametrize("expected", ["ITEM_ALIAS", "13"])
def test_equal_constant_aliases_do_not_hide_a_gift(expected: str) -> None:
    scripts = _scripts(
        f"Entry:\nsetvar VAR_CHOICE, ITEM_POTION\ngoto_if_ne VAR_CHOICE, {expected}, Done\n"
        "giveitem ITEM_POTION\nDone:\nend",
        {"VAR_CHOICE": 0x4000, "ITEM_POTION": 13, "ITEM_ALIAS": 13},
    )
    assert script_offers(scripts, "Entry").offers[0].item == "ITEM_POTION"


def test_special_writes_are_propagated_through_c_wrappers(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "src").mkdir(parents=True)
    (root / "src/specials.c").write_text(
        "void Inner(void) { gSpecialVar_0x8004 = 1; }\nvoid Outer(void) { Inner(); }\n", encoding="utf-8"
    )
    writes = special_writes(root)
    assert writes["Inner"] == frozenset({"VAR_0x8004"})
    assert writes["Outer"] == frozenset({"VAR_0x8004"})


def test_special_writes_do_not_hide_a_later_branch() -> None:
    blocks = parse_scripts(
        "Entry:\nsetvar VAR_0x8004, 5\nspecial ChangeChoice\ngoto_if_eq VAR_0x8004, 1, Gift\nend\n"
        "Gift:\ngiveitem ITEM_POTION\nend",
        "test.inc",
    )
    scripts = Gen3Scripts(blocks, {}, {"ChangeChoice": frozenset({"VAR_0x8004"})})
    assert script_offers(scripts, "Entry").offers[0].item == "ITEM_POTION"


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_all_pinned_object_scripts_are_read(source_cache_ready: None, game: Game) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    repo = Gen3PretRepo(root, game.pret_versions)
    labels = {str(obj.value("script")) for current in repo.maps.values() for obj in current.objects}
    for version, _ in game.pret_versions:
        reader = repo.offers[version]
        for label in sorted(labels):
            result = reader.read(label)
            assert all(offer.paths for offer in result.offers)
            assert set(result.trainers) <= repo.trainers[version].keys()


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_all_pinned_objects_apply_their_presence(source_cache_ready: None, game: Game) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    repo = Gen3PretRepo(root, game.pret_versions)
    for version, _ in game.pret_versions:
        for current in repo.maps.values():
            for obj in current.objects:
                if obj.kind == "clone":
                    continue
                result = repo.offers[version].read_object(obj)
                assert all(offer.paths for offer in result.offers)


def test_pinned_trades_keep_version_differences(source_cache_ready: None) -> None:
    game = next(game for game in GEN3_GAMES if game.pret_repo == "pokefirered")
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    label = "UndergroundPath_NorthEntrance_EventScript_Saige"
    offers = [repo.offers[version].read(label).offers for version, _ in game.pret_versions]
    assert next(offer.pokemon for offer in offers[0] if offer.kind == "trade") == "SPECIES_NIDORAN_F"
    assert next(offer.pokemon for offer in offers[1] if offer.kind == "trade") == "SPECIES_NIDORAN_M"


def test_pinned_remake_gym_reward_keeps_machine_instead_of_message(source_cache_ready: None) -> None:
    game = next(game for game in GEN3_GAMES if game.pret_repo == "pokefirered")
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        result = repo.offers[version].read("PewterCity_Gym_EventScript_Brock")
        gifts = [offer for offer in result.offers if offer.kind == "gift_item"]
        assert gifts
        assert all(offer.item == "ITEM_TM39" and offer.quantity == "1" for offer in gifts)
        assert not result.unresolved
