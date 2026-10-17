"""La curation DS annote des données existantes et refuse toute référence périmée."""

import csv
from pathlib import Path

import pytest

from pokemaps_data import character_curation_gen4
from pokemaps_data.character_actors_gen4 import ActorCatalog, CharacterActor, validate_actors
from pokemaps_data.character_curation_gen4 import curate_characters
from pokemaps_data.pret_gen4_offer_sites import OfferSite
from pokemaps_data.pret_gen4_offers import Gen4Offer, OfferCatalog, OfferStep


def _data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    giver: str = "pokeplatinum:1:0",
    metadata: dict[str, str] | None = None,
) -> None:
    monkeypatch.setattr(character_curation_gen4, "DATA_DIR", tmp_path)
    (tmp_path / "npc_duplicates.csv").write_text("family,text,reason\n", encoding="utf-8")
    row = dict(
        repos="pokeplatinum",
        text="PLACE:object:1",
        action="resolve",
        kind="gift_egg",
        item="",
        pokemon="SPECIES_RIOLU",
        move="",
        source="gift",
        conditions="Œuf remis par Armand",
        reason="Le dialogue du Sbire lance la scène",
        expression=giver,
    )
    row.update(metadata or {})
    with (tmp_path / "npc_offers.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def _catalogs() -> tuple[ActorCatalog, OfferCatalog]:
    giver = CharacterActor("pokeplatinum:1:0", "PLACE", 0, 0, 142, 1, 2, 12, 8, ())
    grunt = CharacterActor("pokeplatinum:1:1", "PLACE", 1, 1, 124, 3, 4, 13, 9, (0,))
    site = OfferSite("PLACE", "object", 1, 3, 4, 0, 0, ())
    step = OfferStep(site, "gift", (Gen4Offer("gift_egg", pokemon="SPECIES_RIOLU", quantity=1),), (), False)
    return ActorCatalog((giver, grunt), ()), OfferCatalog((step,), ())


def test_scene_trigger_does_not_become_the_giver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _data(tmp_path, monkeypatch)
    actors, offers = curate_characters("pokeplatinum", "platinum", *_catalogs())
    assert actors.actors[0].offers == (0,)
    assert actors.actors[1].offers == ()
    assert offers.steps[0].site.event == 1
    assert offers.steps[0].editorial_conditions == ("Œuf remis par Armand",)
    validate_actors(actors, offers)


def test_unknown_giver_stops_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _data(tmp_path, monkeypatch, "pokeplatinum:1:99")
    with pytest.raises(ValueError, match="donneur absent"):
        curate_characters("pokeplatinum", "platinum", *_catalogs())


def test_missing_source_offer_stops_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _data(tmp_path, monkeypatch)
    actors, _ = _catalogs()
    with pytest.raises(ValueError, match="inutilisées"):
        curate_characters("pokeplatinum", "platinum", actors, OfferCatalog((), ()))


def test_interactive_actor_cannot_be_hidden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _data(tmp_path, monkeypatch)
    (tmp_path / "npc_duplicates.csv").write_text(
        "family,text,reason\nplatinum,pokeplatinum:1:1,Test\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="interactif ou permanent"):
        curate_characters("pokeplatinum", "platinum", *_catalogs())


def test_absent_scene_actor_stops_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _data(tmp_path, monkeypatch)
    (tmp_path / "npc_duplicates.csv").write_text(
        "family,text,reason\nplatinum,pokeplatinum:1:99,Test\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="acteur DS absent"):
        curate_characters("pokeplatinum", "platinum", *_catalogs())


@pytest.mark.parametrize("metadata", [{"price": "500"}, {"expression": ""}, {"conditions": "Phrase."}])
def test_invalid_editorial_fields_are_not_silently_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, metadata: dict[str, str]
) -> None:
    _data(tmp_path, monkeypatch, metadata=metadata)
    with pytest.raises(ValueError, match=r"npc_offers\.csv"):
        curate_characters("pokeplatinum", "platinum", *_catalogs())
