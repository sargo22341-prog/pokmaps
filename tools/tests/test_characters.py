"""Personnages, installations et services des cartes : doublons écartés, warps inaccessibles, Casino, fossiles."""

import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.maps_characters import CharacterCuration, CuratedOffer, read_character_curation
from pokemaps_data.pret_models import NpcOffer
from pokemaps_data.pret_source import conditional_lines

RED, BLUE, YELLOW = 1, 2, 3
RED_BLUE, YELLOW_GROUP = 1, 2


def _objects(db: sqlite3.Connection, version_group: int, sprite: str, *maps: str) -> list[tuple[str, int, int]]:
    marks = ", ".join("?" * len(maps))
    return db.execute(
        f"""SELECT m.identifier, o.x, o.y FROM map_object o JOIN map m ON m.id = o.map_id
            WHERE m.version_group_id = ? AND o.sprite = ? AND m.identifier IN ({marks}) ORDER BY m.identifier""",
        (version_group, sprite, *maps),
    ).fetchall()


def _offers(db: sqlite3.Connection, version_group: int, map_identifier: str) -> set[tuple]:
    return set(
        db.execute(
            """SELECT o.kind, o.name_fr, n.kind, i.identifier, p.identifier, n.quantity, n.price, w.identifier,
                 v.identifier
               FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
               LEFT JOIN item i ON i.id = n.item_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
               LEFT JOIN item w ON w.id = n.wanted_item_id LEFT JOIN version v ON v.id = n.version_id
               WHERE m.version_group_id = ? AND m.identifier = ?""",
            (version_group, map_identifier),
        )
    )


@pytest.mark.parametrize("version_group", [RED_BLUE, YELLOW_GROUP])
def test_one_professor_oak_in_pallet_town(db: sqlite3.Connection, version_group: int) -> None:
    """Le Prof. Chen n'est plus dehors ni à l'entrée du labo : seulement au fond, où il donne le Pokémon."""
    oak = _objects(db, version_group, "oak", "pallet-town", "oaks-lab")
    assert [identifier for identifier, _, _ in oak] == ["oaks-lab"]
    assert oak[0][2] == 2 * 16 + 8  # 3e rangée de cases, près des Poké Balls


@pytest.mark.parametrize("version_group", [RED_BLUE, YELLOW_GROUP])
def test_one_old_man_who_teaches_catching(db: sqlite3.Connection, version_group: int) -> None:
    assert _objects(db, version_group, "gambler-asleep", "viridian-city") == []
    old_men = _objects(db, version_group, "gambler", "viridian-city")
    # Le Parieur près de l'arène et le vieil homme de la démonstration de capture.
    assert len(old_men) == 2


def test_one_bill_one_daisy_one_mr_fuji(db: sqlite3.Connection) -> None:
    for version_group in (RED_BLUE, YELLOW_GROUP):
        bill = db.execute(
            """SELECT o.name_fr, o.sprite FROM map_object o JOIN map m ON m.id = o.map_id
               WHERE m.version_group_id = ? AND m.identifier = 'bills-house'""",
            (version_group,),
        ).fetchall()
        assert bill == [("Léo", "super-nerd")]
        assert len(_objects(db, version_group, "daisy", "blues-house")) == 1
        assert _objects(db, version_group, "mr-fuji", "pokemon-tower-7f", "mr-fujis-house") == [
            ("mr-fujis-house", 3 * 16 + 8, 1 * 16 + 8)
        ]


def test_inaccessible_warps_are_not_exported(db: sqlite3.Connection) -> None:
    """À droite du Casino de Céladopole, pret déclare un warp inaccessible vers le 5e étage du Centre Commercial."""
    targets = db.execute(
        """SELECT t.identifier FROM map_warp w JOIN map m ON m.id = w.map_id JOIN map t ON t.id = w.target_map_id
           WHERE m.identifier = 'celadon-city'"""
    ).fetchall()
    assert ("celadon-mart-5f",) not in targets
    assert ("game-corner-prize-room",) in targets


def test_vending_machine_and_drinks_exchange(db: sqlite3.Connection) -> None:
    for version_group in (RED_BLUE, YELLOW_GROUP):
        offers = _offers(db, version_group, "celadon-mart-roof")
        machines = {offer for offer in offers if offer[0] == "vending_machine"}
        assert {(offer[3], offer[6]) for offer in machines} == {
            ("fresh-water", 200),
            ("soda-pop", 300),
            ("lemonade", 350),
        }
        exchanges = {(offer[3], offer[7]) for offer in offers if offer[2] == "exchange"}
        assert exchanges == {("tm13", "fresh-water"), ("tm48", "soda-pop"), ("tm49", "lemonade")}
        assert not any(offer[2] == "gift_item" for offer in offers)
        # Trois distributeurs côte à côte : une seule installation.
        assert scalar_count(db, version_group, "vending_machine") == 1


def scalar_count(db: sqlite3.Connection, version_group: int, kind: str) -> int:
    return db.execute(
        """SELECT count(*) FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND o.kind = ?""",
        (version_group, kind),
    ).fetchone()[0]


def test_game_corner_prizes_differ_between_red_and_blue(db: sqlite3.Connection) -> None:
    prizes = {offer for offer in _offers(db, RED_BLUE, "game-corner-prize-room") if offer[0] == "prize_vendor"}
    assert ("prize_vendor", "Comptoir des lots", "prize_pokemon", None, "scyther", 25, 5500, None, "red") in prizes
    assert ("prize_vendor", "Comptoir des lots", "prize_pokemon", None, "pinsir", 20, 2500, None, "blue") in prizes
    assert ("prize_vendor", "Comptoir des lots", "prize_item", "tm15", None, None, 5500, None, None) in prizes
    yellow = {offer for offer in _offers(db, YELLOW_GROUP, "game-corner-prize-room") if offer[0] == "prize_vendor"}
    assert ("prize_vendor", "Comptoir des lots", "prize_pokemon", None, "vulpix", 18, 1000, None, None) in yellow
    assert scalar_count(db, RED_BLUE, "prize_vendor") == 3
    coins = {offer[2:7] for offer in _offers(db, RED_BLUE, "game-corner") if offer[2] in ("coin_sale", "coin_gift")}
    assert ("coin_sale", None, None, 50, 1000) in coins
    assert ("coin_gift", None, None, 10, None) in coins


def test_fossils_and_services(db: sqlite3.Connection) -> None:
    fossils = {offer[3:6] for offer in _offers(db, RED_BLUE, "cinnabar-lab-fossil-room") if offer[2] == "fossil"}
    assert fossils == {("dome-fossil", "kabuto", 30), ("helix-fossil", "omanyte", 30), ("old-amber", "aerodactyl", 30)}
    for version_group in (RED_BLUE, YELLOW_GROUP):
        assert ("npc", "Maman", "heal", None, None, None, None, None, None) in _offers(
            db, version_group, "reds-house-1f"
        )
        assert ("npc", "Infirmière", "heal", None, None, None, None, None, None) in _offers(
            db, version_group, "viridian-pokecenter"
        )
        assert ("npc", "Expert en surnoms", "name_rater", None, None, None, None, None, None) in _offers(
            db, version_group, "name-raters-house"
        )
    assert ("npc", "Vendeur de vélos", "exchange", "bicycle", None, None, None, "bike-voucher", None) in _offers(
        db, RED_BLUE, "bike-shop"
    )


def test_conditional_lines(tmp_path: Path) -> None:
    source = tmp_path / "prizes.asm"
    source.write_text("db ABRA\nIF DEF(_RED)\ndb SCYTHER ; Rouge\nELSE\ndb PINSIR\nENDC\ndb PORYGON\n", "utf-8")
    assert conditional_lines(source, frozenset({"_RED"})) == ["db ABRA", "db SCYTHER", "db PORYGON"]
    assert conditional_lines(source, frozenset({"_BLUE"})) == ["db ABRA", "db PINSIR", "db PORYGON"]
    source.write_text("IF DEF(_RED)\ndb ABRA\n", "utf-8")
    with pytest.raises(ValueError, match="non terminé"):
        conditional_lines(source, frozenset())


def test_curation_rows_must_match_a_character() -> None:
    curation = read_character_curation()
    assert "TEXT_PALLETTOWN_OAK" in curation.duplicates
    stale = CharacterCuration(
        frozenset({"TEXT_NOBODY"}),
        [CuratedOffer(frozenset({"pokered"}), "TEXT_NOBODY_ELSE", NpcOffer("coin_sale", quantity=50, price=1000))],
    )
    assert stale.unused() == ["doublon:TEXT_NOBODY", "offre:pokered:TEXT_NOBODY_ELSE"]


def test_characters_are_people_objects_or_pokemon(db: sqlite3.Connection) -> None:
    """Le Fossile du Mont Sélénite est un objet, l'Otaria du Fan Club un Pokémon, l'infirmière une personne."""
    kinds = dict(
        db.execute(
            """SELECT o.sprite, o.kind FROM map_object o JOIN map m ON m.id = o.map_id
               WHERE m.version_group_id = ? AND o.sprite IN ('fossil', 'seel', 'nurse') GROUP BY o.sprite""",
            (RED_BLUE,),
        )
    )
    assert kinds == {"fossil": "npc_object", "seel": "npc_pokemon", "nurse": "npc"}


def test_starters_in_professor_oaks_lab(db: sqlite3.Connection) -> None:
    """Rouge et Bleu : une Poké Ball par Pokémon de départ ; Jaune : Pikachu, donné par le Prof. Chen."""
    red_blue = {offer for offer in _offers(db, RED_BLUE, "oaks-lab") if offer[2] == "gift_pokemon"}
    assert red_blue == {
        ("npc_object", "Poké Ball", "gift_pokemon", None, starter, 5, None, None, None)
        for starter in ("bulbasaur", "charmander", "squirtle")
    }
    yellow = {offer for offer in _offers(db, YELLOW_GROUP, "oaks-lab") if offer[2] == "gift_pokemon"}
    assert yellow == {("npc", "Prof. Chen", "gift_pokemon", None, "pikachu", 5, None, None, None)}
