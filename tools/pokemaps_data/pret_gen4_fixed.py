"""Pokémon fixes des lieux DS : combats sauvages lancés par les scripts, avec leur position et leurs conditions.

Les scripts lancent ces combats par StartWildBattle, StartLegendaryBattle, StartGiratinaOriginBattle et
StartFatefulEncounter en Platine, ScrCmd_WildBattle et ScrCmd_LegendaryBattle (commandes 0x124 et 0x2BD) en
Diamant/Perle ; l'espèce puis le niveau sont leurs deux arguments, constantes ou variables lues en suivant le flux
(pret_gen4_flow_values). Diamant/Perle choisit Dialga ou Palkia aux Colonnes Lances selon la version du jeu
(ScrCmd_GetGameVersion, GAME_VERSION de include/config.h) : chaque Pokémon garde donc ses versions.

Le premier combat de Diamant/Perle (ScrCmd_FirstBattle, l'Étourmi du Lac Vérité) n'est pas une capture : il n'est
pas lu ici. La position est celle des événements du lieu dont le script mène au combat : le Pokémon posé (son
drapeau de masquage le retire une fois capturé ou vaincu), la case qu'on examine ou le déclencheur au sol. Au Monde
Distorsion, Giratina est posé par le moteur (pret_gen4_distortion). Les conditions sont celles de chaque chemin qui
mène au combat dans le script (pret_gen4_flow_chains), sans les traduire.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_battles import battle_choices
from .pret_gen4_distortion import DistortionObject, read_distortion_objects
from .pret_gen4_engine_text import c_function
from .pret_gen4_flow import Step, Value, is_var, reachable
from .pret_gen4_flow_chains import Chains, Condition
from .pret_gen4_flow_values import VERSION_SLOT, Choices, values_at
from .pret_gen4_source import c_defines, c_enum, metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Events, Gen4Header

# Commande du combat -> nature du combat (Pokémon sauvage, légendaire, Giratina Originel, rencontre fatidique).
_PLATINUM = {
    "StartWildBattle": "wild",
    "StartLegendaryBattle": "legendary",
    "StartGiratinaOriginBattle": "giratina_origin",
    "StartFatefulEncounter": "fateful",
}
_DIAMOND_PEARL = {"ScrCmd_WildBattle": "wild", "ScrCmd_LegendaryBattle": "legendary"}
_DP_ARGUMENTS = ("u16 species = ScriptGetVar(ctx);", "u16 level = ScriptGetVar(ctx);")
_HIDDEN_ITEM_EVENT = 2
_MAX_LEVEL = 100


@dataclass(frozen=True)
class FixedPokemon:
    versions: tuple[str, ...]
    species: str
    level: int


@dataclass(frozen=True)
class FixedPosition:
    kind: str  # object (Pokémon posé), background (case examinée), trigger (déclencheur au sol)
    x: int
    z: int
    y: int  # unité de l'événement d'origine
    width: int
    length: int
    removal_flag: int | None  # drapeau de masquage du Pokémon posé
    conditions: tuple[Condition, ...]  # variable d'un déclencheur, avancement du Monde Distorsion


@dataclass(frozen=True)
class FixedEncounter:
    header: str
    script_file: int
    step: str
    battle: str
    pokemon: tuple[FixedPokemon, ...]
    positions: tuple[FixedPosition, ...]
    paths: tuple[tuple[Condition, ...], ...]  # conditions de chaque chemin qui mène au combat


def read_fixed_encounters(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> tuple[FixedEncounter, ...]:
    commands = _commands(repo)
    species = _species_names(repo)
    versions = game_versions(repo)
    choices = battle_choices(repo)
    choices = Choices(choices.starters, choices.genders, frozenset(versions))
    distortion = read_distortion_objects(repo) if repo.platinum else ()
    users: dict[int, list[Gen4Header]] = {}
    for index in sorted(headers):
        users.setdefault(headers[index].scripts, []).append(headers[index])
    result = []
    for index, flow in sorted(repo.flows.items()):
        battles = [step for step in flow.steps.values() if step.command in commands]
        if not battles:
            continue
        if index not in users:
            raise ValueError(f"{flow.name} : Pokémon fixe hors des lieux retenus")
        seeds = {int(argument) for step in battles for argument in step.arguments[:2] if is_var(argument)}
        values = values_at(flow, lambda step: step.command in commands, seeds, None, repo.common_scripts, choices)
        chains = Chains(flow)
        for step in battles:
            pokemon = _pokemon(step, values.combos(step.key, (*step.arguments[:2], VERSION_SLOT)), species, versions)
            entries = tuple(
                number for number, entry in enumerate(flow.entries, 1) if step.key in reachable(flow, entry)
            )
            for header in users[index]:
                positions = _positions(repo.events[header.events], header, entries, distortion)
                if not positions:
                    raise ValueError(f"{header.constant} : Pokémon fixe sans position ({step.source})")
                kind = commands[step.command]
                result.append(
                    FixedEncounter(
                        header.constant, index, step.source, kind, pokemon, positions, chains.paths(step.key)
                    )
                )
    return tuple(result)


def _commands(repo: Gen4PretRepo) -> dict[str, str]:
    """Commandes de combat sauvage, vérifiées dans la source : espèce puis niveau."""
    if repo.platinum:
        macros = read_text(repo.root / "asm/macros/scrcmd.inc")
        for name in _PLATINUM:
            if not re.search(rf"\.macro {name} species, level\n", macros):
                raise ValueError(f"{repo.root} : macro {name} absente ou modifiée")
        return _PLATINUM
    names = {command.name for command in repo.script_commands}
    text = read_text(repo.root / "arm9/src/scrcmd.c")
    for name in _DIAMOND_PEARL:
        body = c_function(text, name, "scrcmd.c") if name in names else ""
        if not all(line in body for line in _DP_ARGUMENTS) or body.index(_DP_ARGUMENTS[0]) > body.index(
            _DP_ARGUMENTS[1]
        ):
            raise ValueError(f"{repo.root} : commande {name} absente ou modifiée")
    return _DIAMOND_PEARL


def _species_names(repo: Gen4PretRepo) -> dict[int, str]:
    if repo.platinum:
        values = metang_enum(repo.root / "generated/species.txt")
    else:
        values = c_defines(repo.root / "include/constants/species.h", "SPECIES_")
    return {value: name for name, value in values.items()}


def game_versions(repo: Gen4PretRepo) -> dict[int, str]:
    """Numéro que renvoie GetGameVersion -> version PokéAPI, pour chaque version du dépôt."""
    if repo.platinum:
        values = c_enum(repo.root / "include/constants/versions.h", "Version")
    else:
        values = c_defines(repo.root / "include/config.h", "VERSION_")
    result = {}
    for version, symbol in repo.versions:
        if f"VERSION_{symbol}" not in values:
            raise ValueError(f"{repo.root} : numéro de version absent pour {symbol}")
        result[values[f"VERSION_{symbol}"]] = version
    return result


def _pokemon(
    step: Step, combos: frozenset[tuple[Value, ...]], species: dict[int, str], versions: dict[int, str]
) -> tuple[FixedPokemon, ...]:
    if not combos:
        raise ValueError(f"combat sauvage jamais atteint : {step.source}")
    found: dict[tuple[str, int], set[str]] = {}
    for kind, level, version in combos:
        if not isinstance(kind, int) or kind not in species or not isinstance(level, int):
            raise ValueError(f"Pokémon fixe illisible : {step.source} ({kind}, {level})")
        if not 1 <= level <= _MAX_LEVEL:
            raise ValueError(f"Pokémon fixe de niveau invalide : {step.source} ({level})")
        chosen = {versions[version]} if isinstance(version, int) else set(versions.values())
        found.setdefault((species[kind], level), set()).update(chosen)
    order = list(versions.values())
    return tuple(
        FixedPokemon(tuple(sorted(chosen, key=order.index)), name, level)
        for (name, level), chosen in sorted(found.items())
    )


def _positions(
    events: Gen4Events, header: Gen4Header, entries: tuple[int, ...], distortion: tuple[DistortionObject, ...]
) -> tuple[FixedPosition, ...]:
    result = _event_positions(events, entries)
    for obj in distortion:
        if obj.header != header.constant or obj.script not in entries:
            continue
        shown = obj.flag_condition == "FLAG_COND_NONE" or obj.conditions
        if obj.x is None or obj.z is None or obj.y is None or not shown:
            raise ValueError(f"{obj.name} : position ou condition du Pokémon fixe illisible")
        result.append(FixedPosition("object", obj.x, obj.z, obj.y, 1, 1, obj.hidden_flag, obj.conditions))
    return tuple(result)


def _event_positions(events: Gen4Events, entries: tuple[int, ...]) -> list[FixedPosition]:
    result = [
        FixedPosition("object", obj.x, obj.z, obj.y, 1, 1, obj.hidden_flag or None, ())
        for obj in events.object_events
        if obj.script in entries
    ]
    result += [
        FixedPosition("background", event.x, event.z, event.y, 1, 1, None, ())
        for event in events.bg_events
        if event.script in entries and event.kind != _HIDDEN_ITEM_EVENT
    ]
    result += [
        FixedPosition(
            "trigger",
            event.x,
            event.z,
            event.y,
            event.width,
            event.length,
            None,
            (Condition(f"var:{event.var}", "=", event.value),),
        )
        for event in events.coord_events
        if event.script in entries
    ]
    return result
