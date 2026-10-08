"""Conditions des offres dans les jeux : 1re génération, étapes du scénario (story_events.csv) et base générée."""

import sqlite3
from pathlib import Path

import pytest

from pokemaps_data import story_events
from pokemaps_data.offer_conditions import ALWAYS, Condition, Requirement
from pokemaps_data.pret import PretRepo
from pokemaps_data.sources import pret_dir
from pokemaps_data.story_events import read_story_events

CACHE = Path(__file__).resolve().parent.parent / ".cache"

# Conditions d'une offre de la base : moments, jours et étapes, pour un personnage d'une carte d'un jeu.
_CONDITIONS = """
    SELECT n.time_mask, n.weekday_mask,
           (SELECT group_concat(s.description_fr, ' | ') FROM
              (SELECT description_fr FROM npc_offer_story WHERE npc_offer_id = n.id ORDER BY slot) s)
    FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
    JOIN version_group vg ON vg.id = m.version_group_id
    LEFT JOIN item i ON i.id = n.item_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
    WHERE vg.identifier = ? AND m.identifier = ? AND n.kind = ? AND coalesce(i.identifier, p.identifier, '') = ?
"""


def _conditions(db: sqlite3.Connection, group: str, map_identifier: str, kind: str, thing: str) -> set[tuple]:
    return set(db.execute(_CONDITIONS, (group, map_identifier, kind, thing)).fetchall())


@pytest.fixture(scope="module")
def yellow(source_cache_ready: None) -> PretRepo:
    return PretRepo(pret_dir(CACHE, "pokeyellow"))


def test_gen1_text_branches_give_the_badge_or_event(yellow: PretRepo) -> None:
    (squirtle,) = yellow.npc_offers("TEXT_VERMILIONCITY_OFFICER_JENNY")
    assert squirtle.pokemon == "SQUIRTLE"
    assert squirtle.condition == ALWAYS.requiring("BIT_THUNDERBADGE", True)
    # La Boutique de Jadielle ne vend qu'avec la seconde table de textes, chargée une fois le colis remis.
    assert yellow.conditions.text_tables["TEXT_VIRIDIANMART_CLERK"] == ALWAYS.requiring("EVENT_OAK_GOT_PARCEL", True)


def test_gen1_hidden_character_appears_after_a_scene(yellow: PretRepo) -> None:
    fuji_house = yellow.maps["MR_FUJIS_HOUSE"]
    position = next(i for i, obj in enumerate(fuji_house.objects) if obj.text == "TEXT_MRFUJISHOUSE_MR_FUJI")
    place = yellow.conditions.offer_place("TEXT_MRFUJISHOUSE_MR_FUJI")
    presence = yellow.conditions.presence(fuji_house.label, position, place)
    assert presence == ALWAYS.requiring("TOGGLE_MR_FUJIS_HOUSE_MR_FUJI", True)


def test_story_events_translate_flags_and_refuse_unknown_ones() -> None:
    events = read_story_events()
    condition = Condition(
        requirements=frozenset(
            {Requirement("EVENT_CLEARED_RADIO_TOWER", True), Requirement("ENGINE_TIME_CAPSULE", False)}
        )
    )
    # ENGINE_TIME_CAPSULE est un drapeau du jour : relu, il n'affiche rien.
    assert events.phrases("pokegold", condition, "test") == ("Après la libération de la Tour Radio",)
    with pytest.raises(ValueError, match="EVENT_NOT_READ"):
        events.phrases("pokegold", ALWAYS.requiring("EVENT_NOT_READ", True), "test")
    assert "pokegold:EVENT_GAVE_KENYA" in events.unused({"pokegold"})


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("pokegold,EVENT_A,Après A,,raison\npokegold|pokecrystal,EVENT_A,,,raison\n", "décrit deux fois"),
        ("pokegold,EVENT_A,après A,,raison\n", "phrase mal formée"),
        ("pokegold,EVENT_A,Après A.,,raison\n", "phrase mal formée"),
        ("pokegold,EVENT_A,Après A,,\n", "raison obligatoires"),
    ],
)
def test_story_events_file_is_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, row: str, message: str
) -> None:
    (tmp_path / "story_events.csv").write_text("repos,flag,when_set,when_clear,reason\n" + row, encoding="utf-8")
    monkeypatch.setattr(story_events, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match=message):
        read_story_events()


def test_weekly_and_daily_offers_in_the_database(db: sqlite3.Connection) -> None:
    # Monica, de la Route 40, ne vient que le lundi (bit 1).
    assert _conditions(db, "crystal", "route-40", "gift_item", "sharp-beak") == {(None, 2, None)}
    # Le marchand de soldes du Souterrain : le lundi matin seulement.
    assert _conditions(db, "gold-silver", "goldenrod-underground", "sale", "nugget") == {(1, 2, None)}
    # La CT03 (Malédiction) de Céladopole n'est donnée que la nuit.
    assert _conditions(db, "crystal", "celadon-mansion-roof-house", "gift_item", "tm03") == {(4, None, None)}
    # Le tuteur de Cristal : mercredi et samedi, après la Ligue.
    tutor = _conditions(db, "crystal", "goldenrod-city", "move_tutor", "")
    assert tutor == {(None, 8 | 64, "Après la victoire à la Ligue Pokémon")}


def test_story_steps_in_the_database(db: sqlite3.Connection) -> None:
    viridian = _conditions(db, "red-blue", "viridian-mart", "sale", "poke-ball")
    assert viridian == {(None, None, "Après avoir remis le colis au Prof. Chen")}
    assert _conditions(db, "yellow", "vermilion-city", "gift_pokemon", "squirtle") == {
        (None, None, "Après le badge Foudre")
    }
    # La Boutique de Ville Griotte ne vend des Poké Balls qu'après la remise de l'Œuf Mystère.
    assert _conditions(db, "gold-silver", "cherrygrove-mart", "sale", "poke-ball") == {
        (None, None, "Après avoir remis l'Œuf Mystère au Prof. Orme")
    }
    assert _conditions(db, "gold-silver", "cherrygrove-mart", "sale", "potion") == {(None, None, None)}


def test_crystal_teacher_in_the_walkway_gives_nothing(db: sqlite3.Connection) -> None:
    """Dans Cristal, l'institutrice du passage n'est là que pendant l'agitation du Bois aux Chênes, quand son script
    refuse la CT12 : seule celle du comptoir la donne (npc_offers.csv retire l'offre jamais possible)."""
    sweet_scent = _conditions(db, "crystal", "route-34-ilex-forest-gate", "gift_item", "tm12")
    assert sweet_scent == {(None, None, "Hors de l'agitation du Bois aux Chênes")}
    count = db.execute(
        """SELECT count(*) FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           JOIN version_group vg ON vg.id = m.version_group_id JOIN item i ON i.id = n.item_id
           WHERE vg.identifier = 'crystal' AND m.identifier = 'route-34-ilex-forest-gate' AND i.identifier = 'tm12'"""
    ).fetchone()[0]
    assert count == 1
