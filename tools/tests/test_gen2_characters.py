"""Personnages, installations et offres d'Or et d'Argent (phase 5 de plan_gen_2.md), dans l'aperçu de tous les jeux."""

import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.pret_gen2_scripts import ScriptFile
from pokemaps_data.pret_models import NpcOffer

GOLD_SILVER_GROUP = 3

# Offres d'une carte d'Or et d'Argent : (type d'objet, nom, offre, objet, Pokémon, quantité, prix, demandé, version).
_OFFERS = """
    SELECT o.kind, o.name_fr, n.kind, i.identifier, p.identifier, n.quantity, n.price,
           coalesce(w.identifier, wi.identifier), v.identifier
    FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
    LEFT JOIN item i ON i.id = n.item_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
    LEFT JOIN pokemon w ON w.id = n.wanted_pokemon_id LEFT JOIN item wi ON wi.id = n.wanted_item_id
    LEFT JOIN version v ON v.id = n.version_id
    WHERE m.version_group_id = ? AND m.identifier = ?
"""


def _offers(db: sqlite3.Connection, map_identifier: str) -> list[tuple]:
    return db.execute(_OFFERS, (GOLD_SILVER_GROUP, map_identifier)).fetchall()


def _objects(db: sqlite3.Connection, map_identifier: str) -> list[tuple[str, str, str | None]]:
    return db.execute(
        """SELECT o.kind, o.name_fr, i.identifier FROM map_object o JOIN map m ON m.id = o.map_id
           LEFT JOIN item i ON i.id = o.item_id WHERE m.version_group_id = ? AND m.identifier = ?""",
        (GOLD_SILVER_GROUP, map_identifier),
    ).fetchall()


def test_department_store_clerks_sell_at_item_prices(preview_db: sqlite3.Connection) -> None:
    """Le vendeur des CT du Centre Commercial de Doublonville : prix de data/items/attributes.asm."""
    sales = {(offer[3], offer[6]) for offer in _offers(preview_db, "goldenrod-dept-store-5f") if offer[2] == "sale"}
    assert {("tm41", 3000), ("tm48", 3000), ("tm33", 3000)} <= sales
    bargains = {(offer[3], offer[6]) for offer in _offers(preview_db, "goldenrod-underground") if offer[2] == "sale"}
    # Le marchand de soldes a ses propres prix (data/items/bargain_shop.asm).
    assert ("nugget", 4500) in bargains


def test_gifts_with_held_items_and_egg(preview_db: sqlite3.Connection) -> None:
    starters = {offer for offer in _offers(preview_db, "elms-lab") if offer[2] == "gift_pokemon"}
    assert starters == {
        ("npc_object", "Poké Ball", "gift_pokemon", "oran-berry", starter, 5, None, None, None)
        for starter in ("cyndaquil", "totodile", "chikorita")
    }
    assert ("npc", "Pêcheur", "gift_item", "mystic-water", None, 1, None, None, None) in _offers(
        preview_db, "cherrygrove-city"
    )
    egg = [offer for offer in _offers(preview_db, "violet-pokecenter-1f") if offer[2] == "gift_egg"]
    assert egg == [("npc", "Assistant du Prof. Orme", "gift_egg", None, "togepi", 5, None, None, None)]
    # Le Caratroc prêté à Irisia est donné par le moteur (special GiveShuckle) : relu dans npc_offers.csv.
    assert ("npc", "Rockeur", "gift_pokemon", "oran-berry", "shuckle", 15, None, None, None) in _offers(
        preview_db, "manias-house"
    )


def test_in_game_trade_with_held_item(preview_db: sqlite3.Connection) -> None:
    trades = [offer for offer in _offers(preview_db, "goldenrod-dept-store-5f") if offer[2] == "trade"]
    assert trades == [("npc", "Topdresseur", "trade", "sitrus-berry", "machop", None, None, "drowzee", None)]


def test_fruit_trees_give_one_berry_each(preview_db: sqlite3.Connection) -> None:
    trees = [offer for offer in _offers(preview_db, "route-29") if offer[2] == "fruit_tree"]
    assert trees == [("npc_object", "Arbre fruitier", "fruit_tree", "oran-berry", None, None, None, None, None)]
    count = preview_db.execute(
        """SELECT count(*) FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND n.kind = 'fruit_tree'""",
        (GOLD_SILVER_GROUP,),
    ).fetchone()[0]
    assert count == 30  # data/items/fruit_trees.asm


def test_game_corner_prizes_of_gold_and_silver(preview_db: sqlite3.Connection) -> None:
    prizes = {offer[4:] for offer in _offers(preview_db, "goldenrod-game-corner") if offer[2] == "prize_pokemon"}
    assert prizes == {
        ("abra", 10, 200, None, None),
        ("ekans", 10, 700, None, "gold"),
        ("sandshrew", 10, 700, None, "silver"),
        ("dratini", 10, 2100, None, None),
    }
    coins = {offer[5:7] for offer in _offers(preview_db, "goldenrod-game-corner") if offer[2] == "coin_sale"}
    assert coins == {(50, 1000), (500, 10000)}
    # Céladopole : les lots sont un comptoir (panneau), sans sprite.
    counters = {offer[:3] for offer in _offers(preview_db, "celadon-game-corner-prize-room")}
    assert counters == {
        ("prize_vendor", "Comptoir des lots", "prize_item"),
        ("prize_vendor", "Comptoir des lots", "prize_pokemon"),
    }


def test_facilities_signs_and_hidden_trash(preview_db: sqlite3.Connection) -> None:
    vending = {offer[3:7] for offer in _offers(preview_db, "goldenrod-dept-store-6f") if offer[0] == "vending_machine"}
    assert vending == {("fresh-water", None, None, 200), ("soda-pop", None, None, 300), ("lemonade", None, None, 350)}
    # Quatre distributeurs identiques côte à côte : une seule installation.
    machines = [obj for obj in _objects(preview_db, "goldenrod-dept-store-6f") if obj[0] == "vending_machine"]
    assert len(machines) == 1
    assert ("heal_spot", "Machine de soins", None) in _objects(preview_db, "elms-lab")
    assert ("hidden_item", "Restes", "leftovers") in _objects(preview_db, "celadon-cafe")


def test_services(preview_db: sqlite3.Connection) -> None:
    assert ("npc", "Effaceur de capacités", "move_deleter") in {
        offer[:3] for offer in _offers(preview_db, "move-deleters-house")
    }
    grooming = {
        (offer[1], offer[6]) for offer in _offers(preview_db, "goldenrod-underground") if offer[2] == "grooming"
    }
    assert grooming == {("Coiffeur aîné", 500), ("Coiffeur cadet", 300)}
    assert {offer[1] for offer in _offers(preview_db, "day-care") if offer[2] == "daycare"} == {
        "Gérant de la Pension",
        "Gérante de la Pension",
    }
    # Red soigne l'équipe après son combat pour la fin du jeu : un dresseur ne rend pas de service.
    assert not [offer for offer in _offers(preview_db, "silver-cave-room-3") if offer[2] == "heal"]


def test_curated_offers_and_duplicates(preview_db: sqlite3.Connection) -> None:
    # Peter donne la CS Siphon après les Électrode, que le script de chaque Électrode atteint.
    whirlpool = [offer[:4] for offer in _offers(preview_db, "team-rocket-base-b2f") if offer[3] == "hm06"]
    assert whirlpool == [("npc", "Peter", "gift_item", "hm06")]
    kurt = {offer[3:8] for offer in _offers(preview_db, "kurts-house") if offer[2] == "exchange"}
    assert ("level-ball", None, None, None, "red-apricorn") in kurt
    assert len(kurt) == 7
    # Fargas à son établi est le même personnage : il n'en reste qu'un.
    assert [obj for obj in _objects(preview_db, "kurts-house") if obj[1] == "Fargas"] == [("npc", "Fargas", None)]
    moms = [obj for obj in _objects(preview_db, "players-house-1f") if obj[1] == "Maman"]
    assert moms == [("npc", "Maman", None)]


def test_pokemon_characters_named_by_their_cry(preview_db: sqlite3.Connection) -> None:
    names = {obj[1] for obj in _objects(preview_db, "mr-fujis-house") if obj[0] == "npc_pokemon"}
    assert {"Psykokwak", "Nidorino", "Roucool"} <= names
    beasts = {obj[1] for obj in _objects(preview_db, "burned-tower-b1f") if obj[0] == "npc_pokemon"}
    assert beasts == {"Raikou", "Entei", "Suicune"}


def test_script_prices_and_unknown_specials(gold_silver_repo: Gen2PretRepo, tmp_path: Path) -> None:
    script = tmp_path / "Test.asm"
    script.write_text(
        "DEF TEST_PRICE EQU 500\n"
        "Seller:\n\tsjump .Buy\n.Buy:\n\tcheckmoney YOUR_MONEY, TEST_PRICE\n\tgiveitem MOOMOO_MILK\n"
        "\ttakemoney YOUR_MONEY, TEST_PRICE\n\tend\n"
        "Prize:\n\tgivepoke ABRA, 10\n\ttakecoins 200\n\tend\n"
        "Gift:\n\tverbosegiveitem TM_ROAR, 2\n\tgiveegg TOGEPI, EGG_LEVEL\n\tend\n"
        "Odd:\n\tspecial NotAnOffer\n\tend\n",
        "utf-8",
    )
    reader, script_file = gold_silver_repo.offers, ScriptFile(script)
    assert reader.script_offers(script_file, "Seller").offers == (NpcOffer("sale", item="MOOMOO_MILK", price=500),)
    assert reader.script_offers(script_file, "Prize").offers == (
        NpcOffer("prize_pokemon", pokemon="ABRA", quantity=10, price=200),
    )
    assert reader.script_offers(script_file, "Gift").offers == (
        NpcOffer("gift_item", item="TM_ROAR", quantity=2),
        NpcOffer("gift_egg", pokemon="TOGEPI", quantity=5),
    )
    with pytest.raises(ValueError, match="special non classée : NotAnOffer"):
        reader.script_offers(script_file, "Odd")
