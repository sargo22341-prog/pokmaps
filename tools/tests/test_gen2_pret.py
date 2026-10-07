"""Lecteur pret de la 2e génération (phase 2 de plan_gen_2.md) : cartes, événements, dresseurs et scripts."""

from pathlib import Path

import pytest

from pokemaps_data.pret_gen2 import JOHTO, KANTO, Gen2PretRepo
from pokemaps_data.pret_gen2_scripts import ScriptFile
from pokemaps_data.pret_gen2_trainers import default_moves
from pokemaps_data.pret_models import Connection, MapObject, TrainerPokemon, Warp
from pokemaps_data.pret_source import conditional_annotated_lines, conditional_lines


def test_map_headers_and_tilesets(gold_silver_repo: Gen2PretRepo) -> None:
    repo = gold_silver_repo
    assert len(repo.headers) == 368
    assert len(repo.maps) == 368
    assert len(repo.tilesets) == 28
    numbers = [header.number for header in repo.headers.values()]
    assert sorted(numbers) == list(range(1, 369))  # rang unique : l'identifiant de carte reste unique dans le jeu
    violet = repo.headers["VIOLET_CITY"]
    assert (violet.environment, violet.tileset, violet.landmark, violet.palette) == (
        "TOWN",
        "TILESET_JOHTO",
        "LANDMARK_VIOLET_CITY",
        "PALETTE_AUTO",
    )


def test_a_city_a_route_and_a_cave(gold_silver_repo: Gen2PretRepo) -> None:
    maps = gold_silver_repo.maps
    violet = maps["VIOLET_CITY"]
    assert (violet.width, violet.height, violet.is_outdoor) == (20, 18, True)
    assert violet.connections == [
        Connection("south", "ROUTE_32", 0),
        Connection("west", "ROUTE_36", 0),
        Connection("east", "ROUTE_31", 9),
    ]
    route = maps["ROUTE_30"]
    assert route.connections == [Connection("north", "ROUTE_31", -10), Connection("south", "CHERRYGROVE_CITY", -5)]
    assert route.warps[0] == Warp(7, 39, "ROUTE_30_BERRY_HOUSE", 1)
    cave = maps["UNION_CAVE_1F"]
    assert not cave.is_outdoor
    assert gold_silver_repo.headers["UNION_CAVE_1F"].environment == "CAVE"
    assert len(cave.blocks) == cave.width * cave.height


def test_events_of_route_30(gold_silver_repo: Gen2PretRepo) -> None:
    objects = gold_silver_repo.maps["ROUTE_30"].objects
    assert MapObject(14, 9, "hidden_item", item="POTION") in objects
    joey = next(obj for obj in objects if obj.text == "TrainerYoungsterJoey")
    assert (joey.kind, joey.sprite, joey.trainer_class, joey.trainer_number) == (
        "trainer",
        "SPRITE_YOUNGSTER",
        "YOUNGSTER",
        1,
    )
    tree = next(obj for obj in objects if obj.text == "Route30FruitTree1")
    assert (tree.kind, tree.sprite) == ("npc", "SPRITE_FRUIT_TREE")
    # Le combat de Joey contre Mikey est une scène : ces Pokémon (script commun ObjectEvent) sont des personnages,
    # qui disparaissent une fois le combat vu (drapeau EVENT_ROUTE_30_BATTLE).
    monsters = [obj for obj in objects if obj.sprite == "SPRITE_MONSTER"]
    assert [(obj.kind, obj.event_flag) for obj in monsters] == [("npc", "EVENT_ROUTE_30_BATTLE")] * 2


def test_objects_present_at_some_times_of_day(gold_silver_repo: Gen2PretRepo) -> None:
    # La mère du joueur : au début de la partie (cachée par EVENT_PLAYERS_HOUSE_MOM_1), puis à un endroit différent
    # le matin, le jour et la nuit.
    mom = [obj for obj in gold_silver_repo.maps["PLAYERS_HOUSE_1F"].objects if obj.text == "MomScript"]
    assert [(sorted(obj.times), obj.event_flag) for obj in mom] == [
        ([], "EVENT_PLAYERS_HOUSE_MOM_1"),
        (["MORN"], "EVENT_PLAYERS_HOUSE_MOM_2"),
        (["DAY"], "EVENT_PLAYERS_HOUSE_MOM_2"),
        (["NITE"], "EVENT_PLAYERS_HOUSE_MOM_2"),
    ]
    joey = next(obj for obj in gold_silver_repo.maps["ROUTE_30"].objects if obj.text == "TrainerYoungsterJoey")
    assert (joey.times, joey.event_flag) == (frozenset(), "EVENT_ROUTE_30_YOUNGSTER_JOEY")


def test_item_balls_and_inaccessible_warps(gold_silver_repo: Gen2PretRepo) -> None:
    maps = gold_silver_repo.maps
    items = {(obj.kind, obj.item, obj.text) for obj in maps["ROUTE_32"].objects if obj.item}
    assert items == {
        ("hidden_item", "GREAT_BALL", None),
        ("hidden_item", "SUPER_POTION", None),
        ("item", "GREAT_BALL", "Route32GreatBall"),
        ("item", "POTION", "Route32Potion"),
    }
    # « ; inaccessible » : la maison de test d'Oliville n'est pas atteignable.
    beta = [warp for warp in maps["OLIVINE_CITY"].warps if warp.target == "OLIVINE_HOUSE_BETA"]
    assert [warp.accessible for warp in beta] == [False]
    # Warp -1 : l'arrivée est le warp par lequel on est venu.
    assert {warp.target_warp for warp in maps["CELADON_DEPT_STORE_ELEVATOR"].warps} == {-1}


def test_trainers_from_their_scripts(gold_silver_repo: Gen2PretRepo) -> None:
    repo = gold_silver_repo
    falkner = next(obj for obj in repo.maps["VIOLET_GYM"].objects if obj.text == "VioletGymFalknerScript")
    assert (falkner.kind, falkner.trainer_class, falkner.trainer_number) == ("trainer", "FALKNER", 1)
    assert repo.trainer_parties[("FALKNER", 1)] == [
        TrainerPokemon("PIDGEY", 7, ("TACKLE", "MUD_SLAP")),
        TrainerPokemon("PIDGEOTTO", 9, ("TACKLE", "MUD_SLAP", "GUST")),
    ]
    # Sans attaques écrites : les 4 dernières apprises jusqu'à son niveau (FillMoves).
    assert repo.trainer_parties[("YOUNGSTER", 1)] == [TrainerPokemon("RATTATA", 4, ("TACKLE", "TAIL_WHIP"))]
    # Germignon niveau 15 : Charge (niveau 1) sort quand Poudre Toxik arrive en 5e attaque.
    assert default_moves(repo, "CHIKORITA", 15) == ["GROWL", "RAZOR_LEAF", "REFLECT", "POISONPOWDER"]
    # Rival de la Tour Cendrée : combattu par une scène, son équipe dépend du Pokémon de départ du joueur.
    rival = next(obj for obj in repo.maps["BURNED_TOWER_1F"].objects if obj.sprite == "SPRITE_RIVAL")
    assert (rival.kind, rival.trainer_class, rival.trainer_number) == ("trainer", "RIVAL1", None)
    # Le pêcheur du tutoriel de capture combat lui-même : c'est un personnage.
    dude = next(obj for obj in repo.maps["ROUTE_29"].objects if obj.text == "CatchingTutorialDudeScript")
    assert dude.kind == "npc"


def test_trainer_items(gold_silver_repo: Gen2PretRepo) -> None:
    held = [mon for party in gold_silver_repo.trainer_parties.values() for mon in party if mon.item]
    assert held
    assert all(mon.item != "NO_ITEM" for mon in held)


def test_version_specific_legendaries(gold_silver_repo: Gen2PretRepo) -> None:
    def legendary(const: str) -> list[tuple[str | None, str | None, int | None]]:
        return [
            (obj.version, obj.pokemon, obj.level)
            for obj in gold_silver_repo.maps[const].objects
            if obj.kind == "pokemon"
        ]

    assert legendary("TIN_TOWER_ROOF") == [("gold", "HO_OH", 40), ("silver", "HO_OH", 70)]
    assert legendary("WHIRL_ISLAND_LUGIA_CHAMBER") == [("gold", "LUGIA", 70), ("silver", "LUGIA", 40)]
    assert legendary("VERMILION_CITY") == [(None, "SNORLAX", 50)]


def test_regions_follow_region_check(gold_silver_repo: Gen2PretRepo) -> None:
    region = gold_silver_repo.map_region
    assert region("NEW_BARK_TOWN") == JOHTO
    assert region("PALLET_TOWN") == KANTO
    # RegionCheck range en Johto tout ce qui suit la Route Victoire, Routes 26 à 28 comprises.
    assert region("ROUTE_26") == JOHTO
    assert region("ROUTE_28") == JOHTO
    assert region("ROUTE_22") == KANTO
    assert region("POKECENTER_2F") is None


def test_script_warps_and_player_dependent_sprites(gold_silver_repo: Gen2PretRepo) -> None:
    maps = gold_silver_repo.maps
    assert maps["ROUTE_35_NATIONAL_PARK_GATE"].script_warps == ["NATIONAL_PARK_BUG_CONTEST"]
    assert maps["PLAYERS_HOUSE_2F"].script_warps == []  # warp NONE : le joueur reste sur place
    # Décorations de la chambre et Pokémon de la Pension : ce que le joueur a choisi, pas des personnages.
    sprites = {obj.sprite for pret_map in maps.values() for obj in pret_map.objects}
    assert not {"SPRITE_BIG_DOLL", "SPRITE_DAY_CARE_MON_1"} & sprites
    # Sprite variable : la Simularbre de la Route 36 (apparence de départ, InitializeEventsScript).
    sudowoodo = next(obj for obj in maps["ROUTE_36"].objects if obj.kind == "pokemon")
    assert (sudowoodo.sprite, sudowoodo.pokemon, sudowoodo.level) == ("SPRITE_SUDOWOODO", "SUDOWOODO", 20)


def test_script_reading_follows_branches_and_checkver(tmp_path: Path) -> None:
    path = tmp_path / "Test.asm"
    path.write_text(
        "\n".join(
            [
                "Script:",
                "\tcheckevent EVENT_X",
                "\tiftrue .Done",
                "\tscall Shared",
                "\tcheckver",
                "\tiftrue .Silver",
                "\tgiveitem POTION",
                "\tend",
                ".Silver:",
                "\tgiveitem ETHER",
                "\tend",
                ".Done:",
                "\tjumptext DoneText",
                "Shared:",
                "\tgiveitem REPEL",
                "\tend",
                "Unreached:",
                "\tgiveitem NUGGET",
                "\tend",
            ]
        ),
        encoding="utf-8",
    )
    script = ScriptFile(path)

    def items(checkver: bool | None) -> set[str]:
        lines = script.reachable_lines("Script", checkver)
        return {line.split()[1] for line in lines if line.startswith("giveitem ")}

    assert items(checkver=False) == {"POTION", "REPEL"}
    assert items(checkver=True) == {"ETHER", "REPEL"}
    assert items(checkver=None) == {"POTION", "ETHER", "REPEL"}


def test_unsupported_assembly_conditions_stop_the_reading(tmp_path: Path) -> None:
    path = tmp_path / "Conditional.asm"
    path.write_text("Script:\nIF DEF(_GOLD)\n\tgiveitem POTION\nENDC\n\tend\n", encoding="utf-8")
    with pytest.raises(ValueError, match="condition d'assemblage"):
        ScriptFile(path).has_label("Script")


def test_conditional_lines_resolve_elif_branches(tmp_path: Path) -> None:
    path = tmp_path / "Versions.asm"
    path.write_text(
        "IF DEF(_GOLD)\n\tdb GOLD ; or\nELIF DEF(_SILVER)\n\tdb SILVER\nELSE\n\tdb OTHER\nENDC\n"
        "if DEF(_DEBUG)\n\tdb DEBUG\nendc\n",
        encoding="utf-8",
    )
    assert conditional_lines(path, frozenset({"_GOLD"})) == ["db GOLD"]
    assert conditional_lines(path, frozenset({"_SILVER"})) == ["db SILVER"]
    assert conditional_lines(path, frozenset()) == ["db OTHER"]
    assert conditional_annotated_lines(path, frozenset({"_GOLD", "_DEBUG"})) == [("db GOLD", "or"), ("db DEBUG", "")]
    path.write_text("IF _NARG == 2\n\tdb 0\nENDC\n", encoding="utf-8")
    with pytest.raises(ValueError, match="condition non prise en charge"):
        conditional_lines(path, frozenset())
