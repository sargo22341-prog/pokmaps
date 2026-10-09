"""Équipes GBA, calcul des attaques initiales et métadonnées de combat."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_source import read_text
from .pret_models import TrainerPokemon

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo

_MAX_TRAINERS = 4096


@dataclass(frozen=True)
class Gen3Trainer:
    const: str
    trainer_class: str
    name: str
    double_battle: bool
    items: tuple[str, ...]
    party: tuple[TrainerPokemon, ...]


def _blocks(text: str, pattern: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(pattern, text):
        depth = 1
        end = match.end()
        for position in range(end, len(text)):
            depth += (text[position] == "{") - (text[position] == "}")
            if depth == 0:
                end = position
                break
        else:
            raise ValueError(f"Initialiseur non terminé : {match[1]}")
        if match[1] in result or len(result) >= _MAX_TRAINERS:
            raise ValueError(f"Initialiseur répété ou trop nombreux : {match[1]}")
        result[match[1]] = text[match.end() : end]
    if not result:
        raise ValueError(f"Initialiseurs absents : {pattern}")
    return result


def read_learnsets(repo: Gen3PretRepo, version: str) -> dict[str, tuple[tuple[int, str], ...]]:
    relative = "src/data/pokemon/level_up_learnsets.h"
    text = read_text(repo.root / relative) if repo.ruby else repo.source_text(relative, version)
    bodies = _blocks(text, r"const u16 (\w+)\[\]\s*=\s*\{")
    sets = {label: _learnset(label, body) for label, body in bodies.items()}
    pointer_path = repo.root / "src/data/pokemon/level_up_learnset_pointers.h"
    pointers = read_text(pointer_path)
    if repo.ruby:
        labels = re.findall(r"^\s*(g\w+LevelUpLearnset),?\s*$", pointers, re.M)
        species = {
            name: int(number)
            for name, number in re.findall(
                r"#define\s+(SPECIES_\w+)\s+(\d+)\b", read_text(repo.root / "include/constants/species.h")
            )
        }
        return {name: sets[labels[number]] for name, number in species.items() if number < len(labels)}
    links = re.findall(r"\[(SPECIES_\w+)\]\s*=\s*(\w+)", pointers)
    return {species: sets[label] for species, label in links}


def _learnset(label: str, body: str) -> tuple[tuple[int, str], ...]:
    pattern = r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)\s*,"
    moves = tuple((int(level), move) for level, move in re.findall(pattern, body))
    remaining = re.sub(pattern, "", body).strip()
    if remaining not in {"LEVEL_UP_END", "LEVEL_UP_END,"} or not moves:
        raise ValueError(f"{label} : liste d'attaques absente ou illisible : {remaining}")
    levels = tuple(level for level, _ in moves)
    if levels != tuple(sorted(levels)) or any(not 1 <= level <= 100 for level in levels):
        raise ValueError(f"{label} : niveaux d'apprentissage invalides")
    return moves


def default_moves(learnset: tuple[tuple[int, str], ...], level: int) -> tuple[str, ...]:
    """GiveBoxMonInitialMoveset : les quatre dernières attaques, sans doublon encore connu."""
    if not 1 <= level <= 100:
        raise ValueError(f"Niveau de dresseur invalide : {level}")
    moves: list[str] = []
    for learned_at, move in learnset:
        if learned_at > level:
            break
        if move not in moves:
            moves.append(move)
            if len(moves) > 4:
                moves.pop(0)
    if not moves:
        raise ValueError(f"Aucune attaque au niveau {level}")
    return tuple(moves)


def _party(body: str, learnsets: dict[str, tuple[tuple[int, str], ...]], label: str) -> tuple[TrainerPokemon, ...]:
    # Les accolades des attaques sont retirées pour isoler les initialiseurs de Pokémon.
    flattened = re.sub(r"(\.moves\s*=\s*)\{([^{}]*)\}", r"\1\2", body)
    mons = re.findall(r"\{([^{}]*)\}", flattened, re.S)
    if not 1 <= len(mons) <= 6 or re.sub(r"\{[^{}]*\}", "", flattened, flags=re.S).strip(" \t\r\n,"):
        raise ValueError(f"{label} : équipe absente ou de plus de six Pokémon")
    return tuple(_pokemon(mon, learnsets, label) for mon in mons)


def _pokemon(body: str, learnsets: dict[str, tuple[tuple[int, str], ...]], label: str) -> TrainerPokemon:
    fields = re.findall(r"\.(\w+)\s*=", body)
    if len(fields) != len(set(fields)) or set(fields) - {"iv", "lvl", "level", "species", "heldItem", "moves"}:
        raise ValueError(f"{label} : champs de Pokémon inconnus ou répétés : {fields}")
    species = re.search(r"\.species\s*=\s*(SPECIES_\w+)", body)
    level = re.search(r"\.(?:lvl|level)\s*=\s*(\d+)", body)
    if not species or not level or species[1] not in learnsets:
        raise ValueError(f"{label} : Pokémon illisible : {body}")
    moves_field = re.search(r"\.moves\s*=\s*(.*?)(?=\.\w+\s*=|$)", body, re.S)
    if moves_field:
        raw_moves = re.findall(r"MOVE_\w+", moves_field[1])
        if len(raw_moves) != 4:
            raise ValueError(f"{label} : quatre attaques explicites attendues : {body}")
        moves = tuple(move for move in raw_moves if move != "MOVE_NONE")
    else:
        moves = default_moves(learnsets[species[1]], int(level[1]))
    held = re.search(r"\.heldItem\s*=\s*(ITEM_\w+)", body)
    if "heldItem" in fields and not held:
        raise ValueError(f"{label} : objet tenu illisible : {body}")
    if not 1 <= int(level[1]) <= 100 or not moves:
        raise ValueError(f"{label} : niveau ou attaques invalides : {body}")
    return TrainerPokemon(species[1], int(level[1]), moves, held[1] if held and held[1] != "ITEM_NONE" else None)


def read_trainers(repo: Gen3PretRepo, version: str) -> dict[str, Gen3Trainer]:
    learnsets = read_learnsets(repo, version)
    text = repo.source_text("src/data/trainer_parties.h", version)
    macros = dict(re.findall(r"#define\s+(DUMMY_TRAINER_\w+)\s+((?:[^\n]*\\\n)*[^\n]*)", text))
    for name, body in sorted(macros.items(), key=lambda entry: -len(entry[0])):
        text = re.sub(r"\b" + name + r"\b", body.replace("\\", ""), text)
    parties = _blocks(text, r"const struct TrainerMon\w+ (\w+)\[\]\s*=\s*\{")
    parties = {label: _party(body, learnsets, label) for label, body in parties.items()}
    path = "src/data/trainers_en.h" if repo.ruby else "src/data/trainers.h"
    entries = _blocks(repo.source_text(path, version), r"\[(TRAINER_\w+)\]\s*=\s*\{")
    result = {}
    for const, body in entries.items():
        if const == "TRAINER_NONE":
            continue
        result[const] = _trainer(const, body, parties)
    return result


def _trainer(const: str, body: str, parties: dict[str, tuple[TrainerPokemon, ...]]) -> Gen3Trainer:
    trainer_class = re.search(r"\.trainerClass\s*=\s*(TRAINER_CLASS_\w+)", body)
    name = re.search(r'\.trainerName\s*=\s*_\("([^"]*)"\)', body)
    double = re.search(r"\.doubleBattle\s*=\s*(TRUE|FALSE)", body)
    party = re.search(r"\.party\s*=\s*(?:\w+\((\w+)\)|\{\.\w+\s*=\s*(\w+)\s*\})", body)
    items = re.search(r"\.items\s*=\s*\{([^{}]*)\}", body)
    if not all((trainer_class, name, double, party, items)):
        raise ValueError(f"{const} : dresseur illisible : {body}")
    party_label = party[1] or party[2]
    if party_label not in parties:
        raise ValueError(f"{const} : équipe absente : {party_label}")
    size = re.search(r"\.partySize\s*=\s*(\d+)", body)
    if size and int(size[1]) != len(parties[party_label]):
        raise ValueError(f"{const} : taille de l'équipe incohérente")
    return Gen3Trainer(
        const,
        trainer_class[1],
        name[1],
        double[1] == "TRUE",
        tuple(item for item in re.findall(r"ITEM_\w+", items[1]) if item != "ITEM_NONE"),
        parties[party_label],
    )
