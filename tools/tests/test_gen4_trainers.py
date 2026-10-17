"""Dresseurs, revanches du Cherche VS et objets cachés DS sur des sources réduites des deux dépôts."""

import json
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_field_items import _hidden, _HiddenEntry
from pokemaps_data.pret_gen4_map_models import BgEvent
from pokemaps_data.pret_gen4_rematches import read_vs_seeker
from pokemaps_data.pret_gen4_script_ids import ScriptIds
from pokemaps_data.pret_gen4_trainers import read_trainers

LEARNSET = [[1, "MOVE_TACKLE"], [5, "MOVE_GROWL"], [9, "MOVE_QUICK_ATTACK"], [13, "MOVE_WING_ATTACK"]]
LEARNSET += [[17, "MOVE_DOUBLE_TEAM"], [17, "MOVE_TACKLE"]]
MOVES = ["MOVE_NONE", "MOVE_TACKLE", "MOVE_GROWL", "MOVE_QUICK_ATTACK", "MOVE_WING_ATTACK", "MOVE_DOUBLE_TEAM"]


def write(path: Path, content: str | dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def mon(level: int, moves: list[str] | None = None, item: str | None = None, iv_scale: int = 0) -> dict:
    fields = {"species": "SPECIES_STARLY", "form": 0, "level": level, "item": item, "moves": moves}
    return fields | {"iv_scale": iv_scale, "ball_seal": 0}


def trainer(party: list[dict], double: bool = False) -> dict:
    base = {"name": "Tristan", "class": "TRAINER_CLASS_YOUNGSTER", "items": ["ITEM_POTION"], "ai_flags": []}
    return base | {"double_battle": double, "party": party, "messages": []}


@pytest.fixture()
def platinum(tmp_path: Path) -> Path:
    write(tmp_path / "generated/trainers.txt", "TRAINER_NONE\nTRAINER_YOUNGSTER_A\nTRAINER_YOUNGSTER_B\n")
    write(tmp_path / "generated/moves.txt", "\n".join(MOVES))
    write(tmp_path / "generated/trainer_classes.txt", "TRAINER_CLASS_PLAYER_MALE\nTRAINER_CLASS_YOUNGSTER\n")
    write(tmp_path / "generated/items.txt", "ITEM_NONE\nITEM_POTION\nITEM_ORAN_BERRY\n")
    write(tmp_path / "res/pokemon/starly/data.json", {"learnset": {"by_level": LEARNSET}})
    write(tmp_path / "res/trainers/data/none.json", trainer([]))
    write(tmp_path / "res/trainers/data/youngster_a.json", trainer([mon(17), mon(5, iv_scale=2500)]))
    moves = ["MOVE_GROWL", "MOVE_TACKLE"]
    write(tmp_path / "res/trainers/data/youngster_b.json", trainer([mon(9, moves, "ITEM_ORAN_BERRY", 255)], True))
    return tmp_path


def test_platinum_parties_compute_default_moves_like_the_engine(platinum: Path) -> None:
    trainers = read_trainers(platinum, "pokeplatinum")
    first, second = trainers[1], trainers[2]
    assert first.const == "TRAINER_YOUNGSTER_A" and first.items == ("ITEM_POTION",)
    # BoxPokemon_SetDefaultMoves : la plus ancienne attaque sort quand les quatre emplacements sont pris ; Charge,
    # oubliée au profit de Reflet, revient au même niveau.
    assert first.party[0].move_slots == ("MOVE_QUICK_ATTACK", "MOVE_WING_ATTACK", "MOVE_DOUBLE_TEAM", "MOVE_TACKLE")
    assert first.party[1].moves == ("MOVE_TACKLE", "MOVE_GROWL") and first.party[1].fixed_iv is None
    assert second.double_battle and second.party[0].item == "ITEM_ORAN_BERRY"
    assert second.party[0].move_slots == ("MOVE_GROWL", "MOVE_TACKLE", "MOVE_NONE", "MOVE_NONE")
    assert second.party[0].custom_moves and second.party[0].fixed_iv == 31


def test_platinum_rejects_mixed_parties_and_unknown_moves(platinum: Path) -> None:
    path = platinum / "res/trainers/data/youngster_a.json"
    write(path, trainer([mon(5), mon(5, ["MOVE_TACKLE"])]))
    with pytest.raises(ValueError, match="une partie de l'équipe"):
        read_trainers(platinum, "pokeplatinum")
    write(path, trainer([mon(5, ["MOVE_SURF"])]))
    with pytest.raises(ValueError, match="attaques inconnues"):
        read_trainers(platinum, "pokeplatinum")


@pytest.fixture()
def diamond_pearl(tmp_path: Path) -> Path:
    write(tmp_path / "include/constants/trainer_classes.h", "#define TRAINER_CLASS_YOUNGSTER 1\n")
    write(tmp_path / "files/poketool/waza/waza_tbl.json", {"waza_tbl": [{"name": name} for name in MOVES]})
    write(tmp_path / "files/itemtool/itemdata/item_data.json", {"item_data": [{"name": "ITEM_POTION"}]})
    learnset = [{"move": move.removeprefix("MOVE_"), "level": level} for level, move in LEARNSET]
    write(tmp_path / "files/poketool/personal/wotbl.json", {"wotbl": [{"species": "STARLY", "moves": learnset}]})
    rows = [
        {"index": 0, "type": "TRTYPE_MON", "class": "TRAINER_CLASS_YOUNGSTER", "name": "{TRNAME} -", "party": []},
        {
            "index": 1,
            "type": "TRTYPE_MON",
            "class": "TRAINER_CLASS_YOUNGSTER",
            "name": "{TRNAME}Tristan",
            "doubleBattle": 2,
            "party": [{"difficulty": 0, "level": 5, "species": "SPECIES_STARLY"}],
        },
    ]
    common = {"unk2": 0, "items": [], "unkC": 1, "doubleBattle": 0}
    write(tmp_path / "files/poketool/trainer/trdata.json", {"trdata": [common | row for row in rows]})
    return tmp_path


def test_diamond_pearl_trainers_keep_their_number_and_strip_the_name_marker(diamond_pearl: Path) -> None:
    trainer_one = read_trainers(diamond_pearl, "pokediamond")[1]
    assert (trainer_one.const, trainer_one.name, trainer_one.double_battle) == (None, "Tristan", True)
    assert trainer_one.party[0].moves == ("MOVE_TACKLE", "MOVE_GROWL")
    path = diamond_pearl / "files/poketool/trainer/trdata.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["trdata"][1]["party"][0]["moves"] = ["MOVE_TACKLE"] * 4
    write(path, data)
    with pytest.raises(ValueError, match="forme différente"):
        read_trainers(diamond_pearl, "pokediamond")


def test_platinum_vs_seeker_levels_and_unlock_flags(tmp_path: Path) -> None:
    write(
        tmp_path / "src/overlay005/vs_seeker.c",
        "#define VS_SEEKER_MAX_REMATCHES     6\n#define VS_SEEKER_REMATCH_DATA_NONE 0xFFFF\n"
        "#define VS_SEEKER_REMATCH_DATA_END  0\n#define _ VS_SEEKER_REMATCH_DATA_NONE\n"
        "const VsSeekerRematchData gVsSeekerRematchData[] = {\n    NoUniqueRematches(TRAINER_A),\n"
        "    { TRAINER_B, _, TRAINER_C, _, TRAINER_D, VS_SEEKER_REMATCH_DATA_END },\n};\n",
    )
    cases = "".join(f"case {n}: result = CheckFlag(varsFlags, FLAG_LVL_{n}); break;" for n in range(1, 6))
    signature = "BOOL SystemFlag_CheckUnlockedVsSeekerLevel(VarsFlags *varsFlags, int level)"
    body = f"{signature}\n{{ switch (level) {{ {cases} }} }}"
    write(tmp_path / "src/system_flags.c", body)
    write(tmp_path / "generated/vars_flags.txt", "\n".join(f"FLAG_LVL_{n} = {100 + n}" for n in range(1, 6)))
    rules = read_vs_seeker(tmp_path, "pokeplatinum", {"TRAINER_A": 1, "TRAINER_B": 2, "TRAINER_C": 3, "TRAINER_D": 4})
    assert [series.teams for series in rules.series] == [(1, 1), (2, None, 3, None, 4)]
    assert rules.unlock_flags == (101, 102, 103, 104, 105)


def test_hidden_items_follow_each_engine_lookup() -> None:
    ids = ScriptIds(2000, 1, 3000, 5000, 7000, 8000, 8800, 2, 730, None)
    table = (_HiddenEntry(17, 1, 0x105), _HiddenEntry(4, 3, 0x05), _HiddenEntry(18, 2, 0x05))
    event = BgEvent(8000 + 0x105, 2, 10, 20, 0, 0)
    names = {4: "ITEM_POKE_BALL", 17: "ITEM_POTION", 18: "ITEM_ANTIDOTE"}
    # Platine compare tout le numéro ; Diamant/Perle seulement son octet bas, et garde la première entrée trouvée.
    platinum = _hidden(1, "MAP", event, table, ids, names, platinum=True)
    diamond_pearl = _hidden(1, "MAP", event, table, ids, names, platinum=False)
    assert (platinum.item, platinum.quantity, platinum.flag) == ("ITEM_POTION", 1, 730 + 0x105)
    assert (diamond_pearl.item, diamond_pearl.quantity) == ("ITEM_POKE_BALL", 3)
    with pytest.raises(ValueError, match="hors de la tranche"):
        _hidden(1, "MAP", BgEvent(8800, 2, 0, 0, 0, 0), table, ids, names, platinum=True)


def test_script_ids_name_the_trainer_of_each_battle_script() -> None:
    ids = ScriptIds(2000, 1, 3000, 5000, 7000, 8000, 8800, 2, 730, 1360)
    assert ids.trainer(3000) == (1, False)
    assert ids.trainer(5004) == (5, True)
    assert ids.trainer(7000) is None and ids.trainer(12) is None
