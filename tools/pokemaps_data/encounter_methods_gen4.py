"""Classement explicite des méthodes et conditions de l'aperçu Sinnoh (aucun tirage prédit)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Pokéradar, essaims et double insertion modifient les tables de marche, pas la méthode.
RANDOM_METHODS = frozenset({"walk", "surf", "old-rod", "good-rod", "super-rod", "honey-tree"})
ONE_OFF_METHODS = frozenset(
    {
        "gift",
        "gift-egg",
        "static",
        "roaming-grass",
        "roaming-water",
        "feebas-tile-fishing",
        "npc-trade",
        "pokemon-ranger",
    }
)
CONDITIONS = frozenset(
    {
        "swarm-yes",
        "swarm-no",
        "time-morning",
        "time-day",
        "time-night",
        "radar-on",
        "radar-off",
        "slot2-none",
        "slot2-ruby",
        "slot2-sapphire",
        "slot2-emerald",
        "slot2-firered",
        "slot2-leafgreen",
        "story-progress-beat-galactic-coronet",
        "story-progress-oak-eterna-city",
        "story-progress-hall-of-fame",
        "story-progress-national-dex",
        "story-progress-cure-eldritch-nightmares",
        "other-talk-to-cynthias-grandmother",
        "item-adamant-orb",
        "item-lustrous-orb",
        "item-helix-fossil",
        "item-dome-fossil",
        "item-old-amber",
        "item-root-fossil",
        "item-claw-fossil",
        "story-progress-defeat-jupiter",
        "story-progress-beat-team-galactic-iron-island",
        "other-regirock-regice-registeel-in-party",
        "weekday-friday",
        "story-progress-defeat-mars",
        "item-odd-keystone",
        "other-talked-to-32-people-underground",
        "item-skull-fossil",
        "item-armor-fossil",
        "great-marsh-daily-slot-none",
        "great-marsh-daily-slot-1-of-32",
        "great-marsh-daily-slot-2-of-32",
        "great-marsh-daily-slot-3-of-32",
        "great-marsh-daily-slot-4-of-32",
        "great-marsh-daily-slot-5-of-32",
        "great-marsh-daily-slot-15-of-32",
        "story-progress-before-national-dex",
        "honey-tree-group-a",
        "honey-tree-group-b",
        "honey-tree-group-c",
        "backlot-not-mentioned",
        "backlot-mentioned",
        "other-giratina-not-caught-in-distortion-world",
        "trade-machop",
        "trade-buizel",
        "trade-medicham",
        "trade-finneon",
    }
)


def check_encounter_taxonomy(builder: DatabaseBuilder) -> None:
    slots = builder.api.by_id("encounter_slots")
    methods = builder.api.by_id("encounter_methods")
    encounters = builder.encounters.raw_encounters
    used = {methods[int(slots[int(r["encounter_slot_id"])]["encounter_method_id"])]["identifier"] for r in encounters}
    if unknown := used - RANDOM_METHODS - ONE_OFF_METHODS:
        raise ValueError(f"Méthodes de rencontre DS inconnues : {sorted(unknown)}")
    ids = {r["id"] for r in encounters}
    conditions = builder.api.by_id("encounter_condition_values")
    used_conditions = {
        conditions[int(r["encounter_condition_value_id"])]["identifier"]
        for r in builder.api.table("encounter_condition_value_map")
        if r["encounter_id"] in ids
    }
    # Les tables du moteur remplacent les rencontres aléatoires de PokéAPI : leurs conditions sont classées aussi.
    used_conditions |= {
        conditions[value]["identifier"]
        for data in builder.encounters.gen4_wild.values()
        for encounter in data.encounters
        for value in encounter.conditions
    }
    if unknown := used_conditions - CONDITIONS:
        raise ValueError(f"Conditions de rencontre DS inconnues : {sorted(unknown)}")
