"""Une rencontre ou une personne garde un seul repère, sans perdre ses offres ni équipes."""

from dataclasses import replace
from types import SimpleNamespace

from pokemaps_data.maps_characters import ObjectRow
from pokemaps_data.maps_fixed_gen4 import fixed_rows, merge_actor_poses
from pokemaps_data.maps_offers_gen4 import _scene_targets
from pokemaps_data.maps_trainers_gen3 import _merge_rival_battles
from pokemaps_data.pret_models import NpcOffer, VariantKind


def _row(kind: str = "npc", sprite: str = "45") -> ObjectRow:
    return ObjectRow("ROUTE", kind, 40, 56, sprite, None, None, None, None, source_cell=(2, 3))


def test_daytime_pose_keeps_the_night_battle_and_all_gifts() -> None:
    trainer = _row("trainer")
    trainer.party = [("pikachu", 20, ())]
    npc = replace(_row(), offers=[NpcOffer("gift_item", "potion")])
    [merged] = merge_actor_poses([npc, trainer])
    assert merged.kind == "trainer"
    assert merged.party == trainer.party
    assert merged.offers == npc.offers


def test_two_different_people_on_adjacent_cells_remain_distinct() -> None:
    first = _row()
    second = replace(first, source_cell=(3, 3))
    assert len(merge_actor_poses([first, second])) == 2


def test_fixed_pokemon_versions_are_not_merged_into_one_cartridge() -> None:
    diamond = replace(_row("pokemon", "156"), pokemon="arceus", version="diamond")
    pearl = replace(diamond, version="pearl")
    assert merge_actor_poses([diamond, pearl]) == [diamond, pearl]


def test_scene_reuses_its_unique_giver_and_keeps_distinct_people_separate() -> None:
    row = replace(_row(), key="giver")
    site = SimpleNamespace(header="ROUTE", script_file=1)
    catalog = SimpleNamespace(
        offers=SimpleNamespace(steps=[SimpleNamespace(site=site, step="AddItem")]),
        actors=SimpleNamespace(actors=[SimpleNamespace(key="giver", offers=(0,))]),
    )
    assert _scene_targets(catalog, [row]) == {("ROUTE", 1, "AddItem"): row}
    other = replace(row, key="other", source_cell=(4, 3))
    catalog.actors.actors.append(SimpleNamespace(key="other", offers=(0,)))
    assert _scene_targets(catalog, [row, other]) == {}


def test_alternative_teams_on_one_case_keep_their_held_items() -> None:
    first = replace(_row("trainer"), party=[("pikachu", 20, ())])
    other = replace(first, party=[("raichu", 40, ())], held_items={(1, 1): "oran-berry"})
    [merged] = merge_actor_poses([first, other])
    assert merged.rematches == [other.party]
    assert merged.held_items == {(2, 1): "oran-berry"}


def test_route22_rival_uses_one_actor_and_two_battles_for_each_starter() -> None:
    def battle(level: int) -> ObjectRow:
        return replace(
            _row("trainer"),
            variants=[
                (VariantKind.PLAYER_STARTER, starter, [("pidgey", level, ())])
                for starter in ("bulbasaur", "charmander", "squirtle")
            ],
        )

    row = _merge_rival_battles([battle(47), battle(9)])
    assert row.variant_rematches == {4: 1, 5: 1, 6: 1}
    assert [party[0][1] for _, _, party in row.variants] == [9, 9, 9, 47, 47, 47]


def test_fixed_encounter_uses_posed_arceus_and_only_one_rock_for_spiritomb() -> None:
    names = {493: "Arceus", 442: "Spiritomb"}
    builder = SimpleNamespace(
        api=SimpleNamespace(names=lambda *_: names),
        species={493: {"identifier": "arceus"}, 442: {"identifier": "spiritomb"}},
    )
    position = SimpleNamespace(kind="trigger", x=30, z=35, y=0)
    arceus = SimpleNamespace(species="SPECIES_ARCEUS", level=80, versions=("platinum",))
    spiritomb = SimpleNamespace(species="SPECIES_SPIRITOMB", level=25, versions=("platinum",))
    catalog = SimpleNamespace(
        names=SimpleNamespace(sprites={156: ("Arceus", "pokemon")}),
        actors=SimpleNamespace(
            actors=[
                SimpleNamespace(
                    header="HALL",
                    scene_only=False,
                    graphics=156,
                    x=31,
                    z=27,
                )
            ]
        ),
        fixed=[
            SimpleNamespace(header="HALL", pokemon=[arceus], positions=[position]),
            SimpleNamespace(header="ROUTE", pokemon=[spiritomb], positions=[position] * 4),
        ],
    )
    projection = SimpleNamespace(point=lambda _header, x, z, _height: (x, z))
    arceus_row, spiritomb_row = fixed_rows(builder, catalog, projection)
    assert (arceus_row.x, arceus_row.y, arceus_row.sprite) == (31, 27, "156")
    assert (spiritomb_row.x, spiritomb_row.y) == (30, 35)
