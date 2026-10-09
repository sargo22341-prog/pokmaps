"""Équipes GBA, calcul des attaques initiales et métadonnées de combat."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_script_values import script_constants
from .pret_gen3_source import balanced_bodies, read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo

_MAX_TRAINERS = 4096


@dataclass(frozen=True)
class Gen3TrainerPokemon:
    species: str
    level: int
    move_slots: tuple[str, ...]
    item: str | None
    iv: int
    custom_moves: bool

    @property
    def moves(self) -> tuple[str, ...]:
        return tuple(move for move in self.move_slots if move != "MOVE_NONE")

    @property
    def fixed_iv(self) -> int:
        return self.iv * 31 // 255


@dataclass(frozen=True)
class Gen3Trainer:
    const: str
    trainer_class: str
    name: str
    double_battle: bool
    items: tuple[str, ...]
    party: tuple[Gen3TrainerPokemon, ...]


def _blocks(text: str, pattern: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, body in balanced_bodies(text, pattern, _MAX_TRAINERS):
        if name in result:
            raise ValueError(f"Initialiseur répété : {name}")
        result[name] = body
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


def _party(body: str, learnsets: dict[str, tuple[tuple[int, str], ...]], label: str) -> tuple[Gen3TrainerPokemon, ...]:
    # Les accolades des attaques sont retirées pour isoler les initialiseurs de Pokémon.
    flattened = re.sub(r"(\.moves\s*=\s*)\{([^{}]*)\}", r"\1\2", body)
    mons = re.findall(r"\{([^{}]*)\}", flattened, re.S)
    if not 1 <= len(mons) <= 6 or re.sub(r"\{[^{}]*\}", "", flattened, flags=re.S).strip(" \t\r\n,"):
        raise ValueError(f"{label} : équipe absente ou de plus de six Pokémon")
    return tuple(_pokemon(mon, learnsets, label) for mon in mons)


def _pokemon(body: str, learnsets: dict[str, tuple[tuple[int, str], ...]], label: str) -> Gen3TrainerPokemon:
    fields = re.findall(r"\.(\w+)\s*=", body)
    if len(fields) != len(set(fields)) or set(fields) - {"iv", "lvl", "level", "species", "heldItem", "moves"}:
        raise ValueError(f"{label} : champs de Pokémon inconnus ou répétés : {fields}")
    species = re.search(r"\.species\s*=\s*(SPECIES_\w+)\s*(?:,|$)", body)
    level = re.search(r"\.(?:lvl|level)\s*=\s*(\d+)\s*(?:,|$)", body)
    iv = re.search(r"\.iv\s*=\s*(\d+)\s*(?:,|$)", body)
    if not species or not level or species[1] not in learnsets:
        raise ValueError(f"{label} : Pokémon illisible : {body}")
    if ("iv" in fields and not iv) or (iv and not 0 <= int(iv[1]) <= 255):
        raise ValueError(f"{label} : IV de dresseur invalide : {body}")
    moves_field = re.search(r"\.moves\s*=\s*(.*?)(?=\.\w+\s*=|$)", body, re.S)
    if moves_field:
        raw_moves = tuple(value.strip() for value in moves_field[1].strip().rstrip(",").split(","))
        if len(raw_moves) != 4 or any(not re.fullmatch(r"MOVE_\w+", value) for value in raw_moves):
            raise ValueError(f"{label} : quatre attaques explicites attendues : {body}")
        moves = tuple(raw_moves)
    else:
        moves = default_moves(learnsets[species[1]], int(level[1]))
        moves += ("MOVE_NONE",) * (4 - len(moves))
    held = re.search(r"\.heldItem\s*=\s*(ITEM_\w+)\s*(?:,|$)", body)
    if "heldItem" in fields and not held:
        raise ValueError(f"{label} : objet tenu illisible : {body}")
    if not 1 <= int(level[1]) <= 100 or not any(move != "MOVE_NONE" for move in moves):
        raise ValueError(f"{label} : niveau ou attaques invalides : {body}")
    return Gen3TrainerPokemon(
        species[1],
        int(level[1]),
        moves,
        held[1] if held and held[1] != "ITEM_NONE" else None,
        int(iv[1]) if iv else 0,
        moves_field is not None,
    )


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
    _validate_references(result, script_constants(repo.root))
    return result


def _validate_references(trainers: dict[str, Gen3Trainer], constants: dict[str, int]) -> None:
    for trainer in trainers.values():
        references = list(trainer.items)
        for mon in trainer.party:
            references.extend(mon.moves)
            if mon.item:
                references.append(mon.item)
        if unknown := sorted(set(references) - constants.keys()):
            raise ValueError(f"{trainer.const} : attaques ou objets inconnus : {unknown}")


def _trainer(const: str, body: str, parties: dict[str, tuple[Gen3TrainerPokemon, ...]]) -> Gen3Trainer:
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
    trainer_items = tuple(value.strip() for value in items[1].split(",") if value.strip())
    if len(trainer_items) > 4 or any(not re.fullmatch(r"ITEM_\w+", value) for value in trainer_items):
        raise ValueError(f"{const} : objets de combat illisibles : {items[1]}")
    return Gen3Trainer(
        const,
        trainer_class[1],
        name[1],
        double[1] == "TRUE",
        tuple(item for item in trainer_items if item != "ITEM_NONE"),
        parties[party_label],
    )
