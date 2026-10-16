"""Tables des rencontres, corrigées par les fichiers maintenus dans tools/data/.

Les rencontres viennent de PokéAPI, sauf les rencontres aléatoires des 2e à 4e générations, lues dans pret
(builder_wild_gen2.py, builder_wild_gen3.py et builder_wild_gen4.py), et la pêche de 1re génération que PokéAPI oublie
(builder_fishing_gen1.py). Les rencontres d'événement externe portent la mention
EXTERNAL_EVENT_NOTE. Les lieux et zones sont dans builder_locations.py.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import TYPE_CHECKING

from .builder_fishing_gen1 import check_fishing_rows, gen1_fishing_encounters
from .builder_fixed_gen3 import reconcile_fixed_encounters
from .builder_hoenn_encounters import complete_hoenn_encounters
from .builder_remake_encounters import complete_remake_encounters
from .builder_wild_gen2 import REPLACED_METHODS, BattleNote, WildEncounter, gen2_battle_notes, gen2_wild_encounters
from .builder_wild_gen3 import WildData, gen3_wild_data
from .builder_wild_gen4 import Gen4WildData, complete_gen4_encounters, gen4_wild_data, wild_context
from .games import (
    EXTERNAL_EVENT_AREAS,
    EXTERNAL_EVENT_LOCATIONS,
    EXTERNAL_EVENT_METHODS,
    EXTERNAL_EVENT_NOTE,
    ONE_OFF_METHODS,
    PretFormat,
)
from .pret_gen3_wild import REPLACED_METHODS as GEN3_REPLACED_METHODS
from .pret_gen4_wild import REPLACED_METHODS as GEN4_REPLACED_METHODS
from .pret_gen4_wild import WildContext
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


_CURATION_ACTIONS = frozenset({"exclude", "note", "trade_for", "move_to"})
# Valeurs par défaut de PokéAPI qui restreignent pourtant la rencontre : « time-day » est la valeur par défaut du
# moment de la journée, mais c'est l'une des trois tables des jeux de la 2e génération. Les autres valeurs par défaut
# (pas d'essaim, progression ordinaire, jetons, Pokémon demandé en échange) ne restreignent rien.
_RESTRICTING_DEFAULTS = frozenset({"time-day"})


@dataclass
class EncounterGroup:
    version_id: int
    location_area_id: int
    pokemon_id: int
    method_id: int
    conditions: tuple[int, ...]
    min_level: int
    max_level: int
    chance: float | None
    quantity: int
    notes: list[str] = field(default_factory=list)
    external_event: bool = False

    def add(self, low: int, high: int, rarity: int) -> None:
        """Fusionne un emplacement de rencontre : probabilités cumulées, ou un exemplaire de plus."""
        self.min_level = min(self.min_level, low)
        self.max_level = max(self.max_level, high)
        if self.chance is None:
            self.quantity += 1
        else:
            self.chance += rarity
            self.quantity = 1


class EncounterTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api
        self._rate_moves: dict[tuple[int, int, int], set[int]] = defaultdict(set)

    @cached_property
    def used_areas(self) -> set[int]:
        """Zones des rencontres, y compris celles dont la curation écarte ou déplace toutes les rencontres : leur
        carte reste reliée à la zone (map_areas.csv)."""
        before = {group.location_area_id for group in self._uncurated_groups}
        return before | {group.location_area_id for group in self.encounter_groups}

    # --- Rencontres -------------------------------------------------------------

    @cached_property
    def _pret_versions(self) -> frozenset[int]:
        """Versions dont les rencontres aléatoires sont lues dans pret."""
        versions: set[int] = set()
        for game, vg in zip(self.builder.games, self.builder.vg_ids, strict=True):
            match game.pret_format:
                case PretFormat.GEN1:
                    pass
                case PretFormat.GEN2 | PretFormat.GEN3 | PretFormat.GEN4:
                    rows = self.builder.version_rows
                    versions |= {int(row["id"]) for row in rows if int(row["version_group_id"]) == vg}
        return frozenset(versions)

    @cached_property
    def raw_encounters(self) -> list[dict[str, str]]:
        """Rencontres PokéAPI des jeux configurés, sans celles que pret remplace."""
        slots = self.api.by_id("encounter_slots")
        methods = self.api.by_id("encounter_methods")
        return [
            row
            for row in self.api.table("encounters")
            if int(row["version_id"]) in self.builder.version_ids
            and not (
                int(row["version_id"]) in self._pret_versions
                and methods[int(slots[int(row["encounter_slot_id"])]["encounter_method_id"])]["identifier"]
                in self._replaced_methods(int(row["version_id"]))
            )
        ]

    @cached_property
    def encounter_groups(self) -> list[EncounterGroup]:
        groups = self._apply_curation([replace(group, notes=list(group.notes)) for group in self._uncurated_groups])
        reconcile_fixed_encounters(self.builder, groups)
        complete_hoenn_encounters(self.builder, groups)
        complete_remake_encounters(self.builder, groups)
        complete_gen4_encounters(self.builder, groups, self.gen4_wild)
        _roaming_conditions(groups, self.method_identifiers)
        for note in self._battle_notes:
            _add_battle_note(groups, note)
        locations = self.builder.locations.area_locations
        for group in groups:
            method, location = self.method_identifiers[group.method_id], locations[group.location_area_id]
            area = self.builder.locations.area_keys[group.location_area_id]
            if method in EXTERNAL_EVENT_METHODS or location in EXTERNAL_EVENT_LOCATIONS or area in EXTERNAL_EVENT_AREAS:
                group.external_event = True
                group.notes.insert(0, EXTERNAL_EVENT_NOTE)
        return groups

    @cached_property
    def _uncurated_groups(self) -> list[EncounterGroup]:
        groups: dict[tuple, EncounterGroup] = {}
        pokeapi = self._pokeapi_encounters()
        for encounter in pokeapi + self._pret_encounters(pokeapi):
            key = (
                encounter.version_id,
                encounter.area_id,
                encounter.species_id,
                encounter.method_id,
                encounter.conditions,
            )
            low, high = encounter.min_level, encounter.max_level
            if key not in groups:
                one_off = self.method_identifiers[encounter.method_id] in ONE_OFF_METHODS
                groups[key] = EncounterGroup(*key, low, high, None if one_off else 0.0, 0)
            groups[key].add(low, high, encounter.chance)
        return list(groups.values())

    @cached_property
    def method_identifiers(self) -> dict[int, str]:
        return {int(row["id"]): row["identifier"] for row in self.api.table("encounter_methods")}

    def _pokeapi_encounters(self) -> list[WildEncounter]:
        slots = self.api.by_id("encounter_slots")
        conditions = self._restricting_conditions()
        return [
            WildEncounter(
                int(row["version_id"]),
                int(row["location_area_id"]),
                self.builder.species_of_pokemon[int(row["pokemon_id"])],
                int(slots[int(row["encounter_slot_id"])]["encounter_method_id"]),
                tuple(sorted(conditions[int(row["id"])])),
                int(row["min_level"]),
                int(row["max_level"]),
                int(slots[int(row["encounter_slot_id"])]["rarity"]),
            )
            for row in self.raw_encounters
        ]

    def _pret_encounters(self, pokeapi: list[WildEncounter]) -> list[WildEncounter]:
        encounters: list[WildEncounter] = []
        gen1_games = [game for game in self.builder.games if game.pret_format is PretFormat.GEN1]
        fishing: list[WildEncounter] = []
        for game in self.builder.games:
            match game.pret_format:
                case PretFormat.GEN1:
                    fishing += gen1_fishing_encounters(self.builder, game, pokeapi)
                case PretFormat.GEN2:
                    encounters += gen2_wild_encounters(self.builder, game)
                case PretFormat.GEN3:
                    encounters += list(self.gen3_wild[game.version_group].encounters)
                case PretFormat.GEN4:
                    encounters += list(self.gen4_wild[game.version_group].encounters)
        if gen1_games:
            check_fishing_rows(self.builder, gen1_games, fishing)
        return encounters + fishing

    def _replaced_methods(self, version: int) -> frozenset[str]:
        row = next(row for row in self.builder.version_rows if int(row["id"]) == version)
        match self.builder.game_of(int(row["version_group_id"])).pret_format:
            case PretFormat.GEN3:
                return GEN3_REPLACED_METHODS
            case PretFormat.GEN4:
                return GEN4_REPLACED_METHODS
            case PretFormat.GEN1 | PretFormat.GEN2:
                return REPLACED_METHODS

    @cached_property
    def gen3_wild(self) -> dict[str, WildData]:
        return {
            game.version_group: gen3_wild_data(self.builder, game)
            for game in self.builder.games
            if game.pret_format is PretFormat.GEN3
        }

    @cached_property
    def gen4_contexts(self) -> dict[str, WildContext]:
        """Règles et listes du moteur DS de chaque jeu, partagées par les rencontres et les emplacements."""
        return {
            game.version_group: wild_context(self.builder.gen4_repo(game, "les règles sauvages"))
            for game in self.builder.games
            if game.pret_format is PretFormat.GEN4
        }

    @cached_property
    def gen4_wild(self) -> dict[str, Gen4WildData]:
        return {
            game.version_group: gen4_wild_data(self.builder, game, self.gen4_contexts[game.version_group])
            for game in self.builder.games
            if game.pret_format is PretFormat.GEN4
        }

    @cached_property
    def _battle_notes(self) -> list[BattleNote]:
        notes: list[BattleNote] = []
        for game in self.builder.games:
            match game.pret_format:
                case PretFormat.GEN1 | PretFormat.GEN3 | PretFormat.GEN4:
                    pass
                case PretFormat.GEN2:
                    notes += gen2_battle_notes(self.builder, game)
        return notes

    def _restricting_conditions(self) -> dict[int, set[int]]:
        """Rencontre -> conditions qui la restreignent (heure, essaim…), hors valeurs par défaut sans effet."""
        ignored = {
            int(row["id"])
            for row in self.api.table("encounter_condition_values")
            if row["is_default"] == "1"
            and row["identifier"] not in _RESTRICTING_DEFAULTS
            and row["identifier"] != "tv-option-blue"
        }
        conditions: dict[int, set[int]] = defaultdict(set)
        for row in self.api.table("encounter_condition_value_map"):
            value = int(row["encounter_condition_value_id"])
            if value not in ignored:
                conditions[int(row["encounter_id"])].add(value)
        return conditions

    def _apply_curation(self, groups: list[EncounterGroup]) -> list[EncounterGroup]:
        excluded: set[int] = set()
        with (DATA_DIR / "encounter_curation.csv").open(encoding="utf-8", newline="") as handle:
            for line, row in enumerate(csv.DictReader(handle), start=2):
                if row["action"] not in _CURATION_ACTIONS:
                    raise ValueError(f"encounter_curation.csv:{line} : action inconnue {row['action']}")
                matches = self._curation_matches(groups, row, line)
                if row["action"] == "exclude":
                    excluded.update(matches)
                for index in matches:
                    self._curate(groups[index], row, line)
        return [group for index, group in enumerate(groups) if index not in excluded]

    @cached_property
    def _ids(self) -> dict[str, dict[str, int]]:
        """Table PokéAPI (versions, pokemon_species, encounter_methods) -> identifiant -> id."""
        return {
            table: {row["identifier"]: int(row["id"]) for row in self.api.table(table)}
            for table in ("versions", "pokemon_species", "encounter_methods")
        }

    def _curation_matches(self, groups: list[EncounterGroup], row: dict[str, str], line: int) -> list[int]:
        versions, species = self._ids["versions"], self._ids["pokemon_species"]
        version_ids = [versions[v] for v in row["versions"].split("|") if versions[v] in self.builder.version_ids]
        if not version_ids:
            return []
        if row["location_area"] not in self.builder.locations.area_ids:
            raise ValueError(f"encounter_curation.csv:{line} : zone inconnue {row['location_area']}")
        target = (
            self.builder.locations.area_ids[row["location_area"]],
            species[row["pokemon"]],
            self._ids["encounter_methods"][row["method"]],
        )
        matches = [
            index
            for index, group in enumerate(groups)
            if group.version_id in version_ids and (group.location_area_id, group.pokemon_id, group.method_id) == target
        ]
        if not matches:
            raise ValueError(f"encounter_curation.csv:{line} ne correspond à aucune rencontre : {row}")
        return matches

    def _curate(self, group: EncounterGroup, row: dict[str, str], line: int) -> None:
        match row["action"]:
            case "exclude":
                pass
            case "note":
                group.notes.append(row["value"])
            case "trade_for":
                names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
                group.notes.append(f"Échange contre {names_fr[self._ids['pokemon_species'][row['value']]]}")
            case "move_to":
                if row["value"] not in self.builder.locations.area_ids:
                    raise ValueError(f"encounter_curation.csv:{line} : zone inconnue {row['value']}")
                target = self.builder.locations.area_ids[row["value"]]
                self._rate_moves[(group.version_id, group.location_area_id, group.method_id)].add(target)
                group.location_area_id = target
            case _:
                raise ValueError(f"encounter_curation.csv:{line} : action inconnue {row['action']}")

    @cached_property
    def method_rank(self) -> dict[int, int]:
        return {int(row["id"]): int(row["order"]) for row in self.api.table("encounter_methods")}

    def encounter_tables(self) -> tuple[list[tuple], list[tuple]]:
        groups = sorted(
            self.encounter_groups,
            key=lambda g: (
                g.version_id,
                g.location_area_id,
                self.method_rank[g.method_id],
                g.conditions,
                -(g.chance or 0),
                g.pokemon_id,
            ),
        )
        encounters, conditions = [], []
        for index, group in enumerate(groups, start=1):
            encounters.append(
                (
                    index,
                    group.version_id,
                    group.location_area_id,
                    group.pokemon_id,
                    group.method_id,
                    group.min_level,
                    group.max_level,
                    group.chance,
                    group.quantity,
                    " ; ".join(group.notes) or None,
                    int(group.external_event),
                )
            )
            conditions += [(index, value) for value in group.conditions]
        return encounters, conditions

    def encounter_method_table(self) -> list[tuple]:
        names = self.api.names("encounter_method_prose", "encounter_method_id")
        fixes = self.builder.locations.name_fixes
        used = {group.method_id for group in self.encounter_groups}
        return [
            (
                int(row["id"]),
                row["identifier"],
                fixes.get(("method", row["identifier"])) or names[int(row["id"])],
                int(row["order"]),
                int(row["identifier"] in ONE_OFF_METHODS),
            )
            for row in self.api.table("encounter_methods")
            if int(row["id"]) in used
        ]

    def encounter_condition_value_table(self) -> list[tuple]:
        names = self.api.names("encounter_condition_value_prose", "encounter_condition_value_id")
        used = {value for group in self.encounter_groups for value in group.conditions}
        rows = []
        for row in self.api.table("encounter_condition_values"):
            value = int(row["id"])
            if value not in used:
                continue
            name = self.builder.locations.name_fixes.get(("condition", row["identifier"])) or names.get(value)
            if not name:
                raise ValueError(f"Nom français manquant pour la condition {row['identifier']} (name_fixes.csv)")
            rows.append((value, row["identifier"], name))
        return rows

    def encounter_rate_table(self) -> list[tuple]:
        version_ids, used_areas = self.builder.version_ids, self.used_areas
        present = {(g.version_id, g.location_area_id, g.method_id) for g in self.encounter_groups}
        rates: set[tuple[int, int, int, int]] = set()
        for row in self.api.table("location_area_encounter_rates"):
            version, area, method = (int(row[key]) for key in ("version_id", "location_area_id", "encounter_method_id"))
            if version not in version_ids or area not in used_areas:
                continue
            if version in self._pret_versions and self.method_identifiers[method] in self._replaced_methods(version):
                continue
            key = (version, area, method)
            targets = self._rate_moves.get(key, set())
            # Le taux suit une zone déplacée ; si des rencontres restent à l'origine, elles gardent aussi leur taux.
            if not targets or key in present:
                rates.add((version, area, method, int(row["rate"])))
            rates.update((version, target, method, int(row["rate"])) for target in targets)
        for data in (*self.gen3_wild.values(), *self.gen4_wild.values()):
            for version, area, method, rate in data.rates:
                key = (version, area, method)
                targets = self._rate_moves.get(key, set())
                if not targets or key in present:
                    rates.add((version, area, method, rate))
                rates.update((version, target, method, rate) for target in targets)
        return sorted(rates)


def _add_battle_note(groups: list[EncounterGroup], note: BattleNote) -> None:
    """Ajoute la note d'un combat scripté à la rencontre unique du même Pokémon dans les zones de sa carte."""
    matches = [
        group
        for group in groups
        if group.version_id in note.version_ids
        and group.location_area_id in note.area_ids
        and group.pokemon_id == note.species_id
        and group.chance is None
    ]
    if not matches:
        raise ValueError(f"Combat scripté sans rencontre fixe correspondante : {note}")
    for group in matches:
        group.notes.append(note.note)


def _roaming_conditions(groups: list[EncounterGroup], methods: dict[int, str]) -> None:
    """L'activation d'un errant est commune au sol et à l'eau ; PokéAPI répartit ses conditions entre les deux."""
    conditions: dict[tuple[int, int, int], set[int]] = defaultdict(set)
    for row in groups:
        if methods[row.method_id] not in {"roaming-grass", "roaming-water"}:
            continue
        key = (row.version_id, row.location_area_id, row.pokemon_id)
        conditions[key].update(row.conditions)
    for row in groups:
        if methods[row.method_id] in {"roaming-grass", "roaming-water"}:
            row.conditions = tuple(sorted(conditions[(row.version_id, row.location_area_id, row.pokemon_id)]))
