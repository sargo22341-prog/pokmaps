"""Les résultats éditoriaux suivent les tables C et les branches des scripts épinglés."""

import re
from pathlib import Path

from pokemaps_data.character_curation_gen3 import Gen3Curation, read_gen3_curation
from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.sources import pret_dir


def _table(root: Path, path: str, name: str, prefix: str) -> tuple[str, ...]:
    text = (root / path).read_text(encoding="utf-8")
    body = text.split(name, 1)[1].split("};", 1)[0]
    return tuple(re.findall(prefix + r"\w+", body))


def test_emerald_prize_pools_and_tutor_prices_match_engine(source_cache_ready: None) -> None:
    game = GEN3_GAMES[1]
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", "pokeemerald"), game.pret_versions)
    curation = read_gen3_curation()
    lady = curation.rows_for("pokeemerald", "LilycoveCity_PokemonCenter_1F:LOCALID_LILYCOVE_LADY")
    for expression, table in (("VAR_0x8004", "sFavorLadyPrizes[]"), ("VAR_0x8005", "sQuizLadyPrizes[]")):
        actual = {row.item for row in lady if row.expression == expression and row.kind == "gift_item"}
        assert actual == set(_table(repo.root, "src/data/lilycove_lady.h", table, "ITEM_"))
    custom = [row for row in lady if row.kind == "gift_custom_item"]
    assert len(custom) == 1 and custom[0].item is None and custom[0].conditions
    text = (repo.root / "src/lilycove_lady.c").read_text(encoding="utf-8")
    assert "sQuizLadyPtr->prize = gSpecialVar_ItemId;" in text
    _check_pyramid(repo, curation)
    _check_frontier_tutors(repo, curation)


def _check_pyramid(repo: Gen3PretRepo, curation: Gen3Curation) -> None:
    rows = curation.rows_for("pokeemerald", "Any:1", "BattlePyramid_FindItemBall")
    pools = set(_table(repo.root, "src/battle_pyramid.c", "sPickupItemsLvl50[", "ITEM_"))
    pools.update(_table(repo.root, "src/battle_pyramid.c", "sPickupItemsLvlOpen[", "ITEM_"))
    assert {row.item for row in rows} == pools
    assert all(row.quantity == "1" and row.conditions for row in rows)
    text = (repo.root / "src/battle_pyramid.c").read_text(encoding="utf-8")
    body = text.split("static void SetPickupItem(void)\n{", 1)[1].split("\n}", 1)[0]
    assert "gSpecialVar_0x8001 = 1;" in body
    assert "sPickupItemsLvlOpen[round]" in body and "sPickupItemsLvl50[round]" in body


def _check_frontier_tutors(repo: Gen3PretRepo, curation: Gen3Curation) -> None:
    script = (repo.root / "data/maps/BattleFrontier_Lounge7/scripts.inc").read_text(encoding="utf-8")
    for index in (1, 2):
        moves = _table(repo.root, "src/field_specials.c", f"sBattleFrontier_TutorMoves{index}[]", "MOVE_")
        rows = curation.rows_for("pokeemerald", f"BattleFrontier_Lounge7:{index + 1}")
        assert tuple(row.move for row in rows) == moves
        costs = (16, 24, 24, 24, 48, 48, 48, 48, 48, 48) if index == 1 else (16, 24, 24, 24, 24, 48, 48, 48, 48, 48)
        assert tuple(row.price for row in rows) == costs
        for move, cost in zip(moves, costs, strict=True):
            label = "BattleFrontier_Lounge7_EventScript_" + move.removeprefix("MOVE_").title().replace("_", "")
            if move == "MOVE_SOFT_BOILED":
                label = "BattleFrontier_Lounge7_EventScript_Softboiled"
            body = script.split(label + "::", 1)[1].split("\n\n", 1)[0]
            assert f"setvar VAR_0x8008, {cost}" in body


def test_news_branches_and_cape_brink_restrictions_match_engine(source_cache_ready: None) -> None:
    game = GEN3_GAMES[2]
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", "pokefirered"), game.pret_versions)
    curation = read_gen3_curation()
    _check_news(repo, curation)
    rows = curation.rows_for("pokefirered", "TwoIsland_CapeBrink_House:LOCALID_CAPE_BRINK_TUTOR")
    expected = ("SPECIES_VENUSAUR", "SPECIES_CHARIZARD", "SPECIES_BLASTOISE")
    assert tuple(row.pokemon for row in rows) == expected
    text = (repo.root / "src/field_specials.c").read_text(encoding="utf-8")
    body = text.split("bool8 CapeBrinkGetMoveToTeachLeadPokemon(void)", 1)[1].split("bool8 HasLearnedAllMoves", 1)[0]
    assert "MON_DATA_FRIENDSHIP) != 255" in body
    for row in rows:
        assert row.move in body and row.required_flag in body
        assert "255" in " ".join(row.conditions)


def _check_news(repo: Gen3PretRepo, curation: Gen3Curation) -> None:
    rows = curation.rows_for("pokefirered", "CeruleanCity_House4:LOCALID_WONDER_NEWS_BERRY_MAN")
    constants = repo.offers["firered"].scripts.constants
    script = (repo.root / "data/maps/CeruleanCity_House4/scripts.inc").read_text(encoding="utf-8").splitlines()
    for line, first, quantity in (
        (32, "ITEM_RAZZ_BERRY", "1"),
        (41, "ITEM_RAZZ_BERRY", "4"),
        (58, "ITEM_CHERI_BERRY", "1"),
        (67, "ITEM_CHERI_BERRY", "4"),
    ):
        selected = [row for row in rows if row.source.endswith(f":{line}")]
        assert len(selected) == 15
        assert {constants[row.item] for row in selected} == set(range(constants[first], constants[first] + 15))
        command = "giveitem REWARD_ITEM" if quantity == "1" else f"giveitem REWARD_ITEM, {quantity}"
        assert script[line - 1].strip() == command
        assert all("500" in " ".join(row.conditions) for row in selected)
    text = (repo.root / "src/wonder_news.c").read_text(encoding="utf-8")
    assert "(Random() % 15) + ITEM_TO_BERRY(ITEM_RAZZ_BERRY)" in text
    assert "(Random() % 15) + ITEM_TO_BERRY(ITEM_CHERI_BERRY)" in text
    assert "#define MAX_REWARD 5" in text and "#define MAX_SENT_REWARD 4" in text
    assert "IsMysteryGiftEnabled()" in text and "ValidateSavedWonderNews()" in text
    assert "++(*stepCounter) >= 500" in text
