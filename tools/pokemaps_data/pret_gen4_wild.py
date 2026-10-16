"""Rencontres sauvages DS lues comme le moteur : tables des en-têtes (pret_gen4_encounter_tables), probabilités et
remplacements du moteur (pret_gen4_wild_rules), listes de l'archive encdata_ex (pret_gen4_wild_extra).

Chaque mécanisme qui remplace des emplacements devient une condition PokéAPI : moment de la journée (le matin garde
la table de base), essaim (lieux de la liste du moteur seulement), Pokéradar (lieux à hautes herbes), cartouche
GBA, M. Backlot au Jardin Trophée. Le Pokémon du jour du Grand Marais n'est jamais prédit : chacune des 32 entrées
de la liste du moteur reçoit sa part de la probabilité des deux emplacements remplacés.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_encounter_tables import EncounterTable, WaterSlot
from .pret_gen4_wild_extra import HONEY_FIRST, MARSH_LOCAL, MARSH_NATIONAL, TROPHY_GARDEN
from .pret_gen4_wild_rules import GBA_GAMES, WildRules

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

REPLACED_METHODS = frozenset({"walk", "surf", "old-rod", "good-rod", "super-rod", "honey-tree"})
_SHELLOS, _GASTRODON, _UNOWN = 422, 423, 201
_HONEY_GROUPS = ("honey-tree-group-a", "honey-tree-group-b", "honey-tree-group-c")
UNOWN_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ!?"


@dataclass(frozen=True)
class Gen4Slot:
    species: int
    min_level: int
    max_level: int
    chance: float
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Gen4WildTable:
    header: int
    method: str
    rate: int  # taux de déclenchement du moteur ; 0 pour les arbres à Miel, tentés à chaque visite
    slots: tuple[Gen4Slot, ...]
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.slots or any(not 1 <= slot.species <= 493 for slot in self.slots):
            raise ValueError(f"table sauvage DS {self.header}/{self.method} : espèce invalide")
        if any(not 1 <= slot.min_level <= slot.max_level <= 100 for slot in self.slots):
            raise ValueError(f"table sauvage DS {self.header}/{self.method} : niveaux invalides")


@dataclass(frozen=True)
class WildContext:
    """Ce que le moteur consulte en plus de la table : règles, listes encdata_ex et lieux à hautes herbes."""

    rules: WildRules
    extra: dict[int, tuple[int, ...]]
    radar_headers: frozenset[int]


def wild_tables(repo: Gen4PretRepo, context: WildContext, version: str) -> tuple[Gen4WildTable, ...]:
    """Tables sauvages de `version`, par en-tête, dans l'ordre des en-têtes."""
    if version not in dict(repo.versions):
        raise ValueError(f"{repo.root} : version DS inconnue : {version}")
    tables = repo.encounters["platinum" if repo.platinum else version]
    result: list[Gen4WildTable] = []
    for index, header in sorted(repo.headers.items()):
        number = dict(header.encounters).get(version)
        if number is None:
            continue
        if number not in tables:
            raise ValueError(f"{header.constant} : table de rencontres {number} absente")
        table = tables[number]
        built = []
        if table.land_rate:
            built.append(("walk", table.land_rate, _walk(index, table, context)))
        if table.surf_rate:
            built.append(("surf", table.surf_rate, _water(table.surf, context.rules.rates.surf)))
        for (rod, rate, slots), (method, rates) in zip(table.rods, context.rules.rates.rods, strict=True):
            if rate:
                if method != f"{rod}-rod":
                    raise ValueError(f"{header.constant} : canne {rod} hors de l'ordre du moteur")
                built.append((method, rate, _water(slots, rates)))
        result.extend(
            Gen4WildTable(index, method, rate, slots, _form_note({s.species for s in slots}, table, context.rules))
            for method, rate, slots in built
        )
    result.extend(_honey_tables(repo, context, version))
    return tuple(result)


def _walk(header: int, table: EncounterTable, context: WildContext) -> tuple[Gen4Slot, ...]:
    rules, replaced = context.rules, context.rules.replacements
    result: list[Gen4Slot] = []
    for index, ((level, species), chance) in enumerate(zip(table.land, rules.rates.land, strict=True)):
        base = Gen4Slot(species, level, level, chance)
        if index in replaced.time:
            result.extend(_alternatives(base, index, replaced.time, _time_choices(table)))
        elif index in replaced.swarm and header in rules.swarm_headers:
            choices = (("swarm-no", None), ("swarm-yes", table.swarms))
            result.extend(_alternatives(base, index, replaced.swarm, choices))
        elif index in replaced.radar and header in context.radar_headers:
            choices = (("radar-off", None), ("radar-on", table.radar))
            result.extend(_alternatives(base, index, replaced.radar, choices))
        elif index in replaced.daily and header == rules.trophy_garden:
            result.append(Gen4Slot(species, level, level, chance, ("backlot-not-mentioned",)))
            mentioned = ("backlot-mentioned", "story-progress-national-dex")
            result.extend(_daily(context.extra[TROPHY_GARDEN], level, chance, mentioned))
        elif index in replaced.daily and header in rules.great_marsh:
            # Le Safari est toujours actif dans le Grand Marais : l'emplacement de base n'apparaît jamais.
            local, national = context.extra[MARSH_LOCAL], context.extra[MARSH_NATIONAL]
            result.extend(_daily(local, level, chance, ("story-progress-before-national-dex",)))
            result.extend(_daily(national, level, chance, ("story-progress-national-dex",)))
        elif index in replaced.dual_slot:
            gba = dict(table.gba)
            choices = (("slot2-none", None), *((f"slot2-{game}", gba[game]) for game in GBA_GAMES))
            result.extend(_alternatives(base, index, replaced.dual_slot, choices))
        else:
            result.append(base)
    return tuple(result)


def _time_choices(table: EncounterTable) -> tuple[tuple[str, tuple[int, ...] | None], ...]:
    return (("time-morning", None), ("time-day", table.day), ("time-night", table.night))


def _alternatives(
    base: Gen4Slot,
    index: int,
    replaced: tuple[int, ...],
    choices: tuple[tuple[str, tuple[int, ...] | None], ...],
) -> list[Gen4Slot]:
    """Une ligne par valeur de la condition : l'espèce de base (None) ou celle qui remplace l'emplacement. Si toutes
    les valeurs donnent l'espèce de base, la condition ne change rien à cet emplacement : il reste sans condition."""
    position = replaced.index(index)
    if all(species is None or species[position] == base.species for _, species in choices):
        return [base]
    return [
        Gen4Slot(
            base.species if species is None else species[position],
            base.min_level,
            base.max_level,
            base.chance,
            (condition,),
        )
        for condition, species in choices
    ]


def _daily(species: tuple[int, ...], level: int, chance: int, conditions: tuple[str, ...]) -> list[Gen4Slot]:
    return [Gen4Slot(value, level, level, chance / len(species), conditions) for value in species]


def _water(slots: tuple[WaterSlot, ...], rates: tuple[int, ...]) -> tuple[Gen4Slot, ...]:
    # GetWildMonLevel accepte des bornes inversées : le niveau est tiré entre la plus petite et la plus grande.
    return tuple(
        Gen4Slot(slot.species, min(slot.level_min, slot.level_max), max(slot.level_min, slot.level_max), rate)
        for slot, rate in zip(slots, rates, strict=True)
    )


def _honey_tables(repo: Gen4PretRepo, context: WildContext, version: str) -> list[Gen4WildTable]:
    honey = context.rules.honey
    members = dict(honey.tables)["platinum" if repo.platinum else version]
    low, high = honey.levels
    slots = tuple(
        Gen4Slot(species, low, high, rate, (group,))
        for group, member in zip(_HONEY_GROUPS, members, strict=True)
        for species, rate in zip(context.extra[member], honey.slot_rates, strict=True)
    )
    if members[0] < HONEY_FIRST:
        raise ValueError(f"{repo.root} : tables des arbres à Miel inconnues : {members}")
    note = honey_note(context.rules)
    return [Gen4WildTable(header, "honey-tree", 0, slots, note) for header in sorted(set(honey.headers))]


def honey_note(rules: WildRules) -> str:
    # Groupes dans l'ordre du moteur : aucun Pokémon, A, B, C.
    (none, a, b, _), (rare_none, rare_a, rare_b, rare_c) = rules.honey.normal_groups, rules.honey.munchlax_groups
    return (
        f"Groupe tiré quand on étale le Miel : arbre ordinaire, A {a} %, B {b} %, rien {none} % ; arbre à Goinfrex "
        f"(4 des 21 arbres, selon le numéro de dresseur), A {rare_a} %, B {rare_b} %, C {rare_c} %, "
        f"rien {rare_none} %."
    )


def _form_note(species: set[int], table: EncounterTable, rules: WildRules) -> str | None:
    notes = []
    if _UNOWN in species:
        group = max(table.form_rates[5] - 1, 0)
        letters = ", ".join(UNOWN_LETTERS[form] for form in rules.unown_forms[group])
        notes.append(f"Formes de Zarbi : {letters}.")
    for value, rate, name in (
        (_SHELLOS, table.form_rates[0], "Sancoki"),
        (_GASTRODON, table.form_rates[1], "Tritosor"),
    ):
        if value in species:
            notes.append(f"{name} Mer {'Orient' if rate else 'Occident'}.")
    return " ".join(notes) or None
