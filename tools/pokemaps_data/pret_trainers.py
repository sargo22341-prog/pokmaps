"""Équipes et attaques des dresseurs de Rouge, Bleu et Jaune."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_models import TrainerPokemon
from .pret_source import macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret import PretRepo

# Champions d'arène dans l'ordre de wGymLeaderNo (LoneMoves de Rouge / Bleu), avec leur équipe d'arène.
GYM_LEADERS = ("BROCK", "MISTY", "LT_SURGE", "ERIKA", "KOGA", "SABRINA", "BLAINE", "GIOVANNI")
GYM_LEADER_PARTIES = frozenset((leader, 3 if leader == "GIOVANNI" else 1) for leader in GYM_LEADERS)


def base_moves(repo: PretRepo) -> dict[str, tuple[str, ...]]:
    """Pokémon -> attaques connues au niveau 1 (data/pokemon/base_stats)."""
    result = {}
    species_re = re.compile(r"^\s*db\s+DEX_(\w+)")
    moves_re = re.compile(r"^\s*db\s+([\w,\s]+?)\s*;\s*level 1 learnset")
    for path in sorted(repo.path("data/pokemon/base_stats").glob("*.asm")):
        species = moves = None
        for raw in path.read_text("utf-8").splitlines():
            if species is None and (match := species_re.match(raw)):
                species = match.group(1)
            elif match := moves_re.match(raw):
                moves = tuple(m.strip() for m in match.group(1).split(",") if m.strip() != "NO_MOVE")
        if species and moves is not None:
            result[species] = moves
    return result


def learnsets(repo: PretRepo) -> dict[str, list[tuple[int, str]]]:
    """Pokémon -> attaques apprises par niveau, dans l'ordre (data/pokemon/evos_moves.asm)."""
    lines = source_lines(repo.path("data/pokemon/evos_moves.asm"))
    # Les labels portent le nom du Pokémon (NidoranMEvosMoves -> NIDORAN_M).
    species = {const.replace("_", ""): const for const in repo.consts("constants/pokemon_constants.asm")}
    by_label = {
        label: species[label.removesuffix("EvosMoves").upper()]
        for label in (line.split()[1] for line in lines if line.startswith("dw ") and line.endswith("EvosMoves"))
        if label.removesuffix("EvosMoves").upper() in species
    }
    result: dict[str, list[tuple[int, str]]] = {}
    current = None
    zeros = 0
    for line in lines:
        if line.endswith(":") and line[:-1] in by_label:
            current, zeros = by_label[line[:-1]], 0
            result[current] = []
        elif current and line.startswith("db "):
            args = macro_args(line, "db")
            if args == ["0"]:
                zeros += 1
                if zeros == 2:
                    current = None
            elif zeros == 1 and len(args) == 2:
                result[current].append((parse_int(args[0]), args[1]))
    return result


def default_moves(repo: PretRepo, species: str, level: int) -> list[str]:
    """Attaques d'un Pokémon de dresseur à ce niveau (WriteMonMoves : les 4 dernières apprises)."""
    moves = list(repo.base_moves.get(species, ()))
    for learn_level, move in repo.learnsets.get(species, []):
        if learn_level > level or move in moves:
            continue
        if len(moves) == 4:
            moves.pop(0)
        moves.append(move)
    return moves


def trainer_parties(repo: PretRepo) -> dict[tuple[str, int], list[TrainerPokemon]]:
    """(classe, numéro) -> équipe, attaques comprises (data/trainers/parties.asm et special_moves.asm)."""
    lines = source_lines(repo.path("data/trainers/parties.asm"))
    classes = repo.consts("constants/trainer_constants.asm", "trainer_const")[1:]
    labels = [line.split()[1] for line in lines if line.startswith("dw ") and line.endswith("Data")]
    by_label = dict(zip(labels, classes, strict=True))
    raw: dict[tuple[str, int], list[tuple[int, str]]] = {}
    current = None
    number = 0
    for line in lines:
        if line.endswith(":") and line[:-1] in by_label:
            current, number = by_label[line[:-1]], 0
        elif current and line.startswith("db "):
            args = macro_args(line, "db")
            if args[-1] != "0":
                raise ValueError(f"parties.asm : équipe non terminée par 0 : {line}")
            number += 1
            args = args[:-1]
            if args[0] == "$FF":
                pairs = [(parse_int(args[i]), args[i + 1]) for i in range(1, len(args), 2)]
            else:
                pairs = [(parse_int(args[0]), species) for species in args[1:]]
            raw[(current, number)] = pairs
    parties = {
        key: [[species, level, repo.default_moves(species, level)] for level, species in pairs]
        for key, pairs in raw.items()
    }
    _apply_special_moves(repo, parties, raw)
    return {
        key: [TrainerPokemon(species, level, tuple(moves)) for species, level, moves in party]
        for key, party in parties.items()
    }


def _apply_special_moves(repo: PretRepo, parties: dict, raw: dict) -> None:
    def put(key: tuple[str, int], mon: int, slot: int, move: str) -> None:
        party = parties.get(key)
        if party is None or mon >= len(party):
            return
        moves = party[mon][2]
        while len(moves) <= slot:
            moves.append("NO_MOVE")
        moves[slot] = move

    lines = source_lines(repo.path("data/trainers/special_moves.asm"))
    if any(line.startswith("SpecialTrainerMoves") for line in lines):
        # Jaune : « db classe, numéro » puis « db Pokémon, emplacement, attaque » (à partir de 1), « db 0 ».
        key = None
        for line in lines:
            if not line.startswith("db "):
                continue
            args = macro_args(line, "db")
            if len(args) == 2:
                key = (args[0], parse_int(args[1]))
            elif len(args) == 3 and key:
                put(key, parse_int(args[0]) - 1, parse_int(args[1]) - 1, args[2])
    else:
        # Rouge / Bleu : attaque unique d'un champion d'arène (LoneMoves, 3e attaque du Pokémon n + 1)
        # et attaque du Conseil 4 (TeamMoves, 3e attaque du 5e Pokémon).
        section = None
        lone = []
        team = {}
        for line in lines:
            if line.endswith(":"):
                section = line[:-1]
            elif line.startswith("db "):
                args = macro_args(line, "db")
                if section == "LoneMoves" and len(args) == 2:
                    lone.append((parse_int(args[0]), args[1]))
                elif section == "TeamMoves" and len(args) == 2:
                    team[args[0]] = args[1]
        for leader, (mon, move) in zip(GYM_LEADERS, lone, strict=False):
            for key in raw:
                if key[0] == leader and key in GYM_LEADER_PARTIES:
                    put(key, mon, 2, move)
        for trainer_class, move in team.items():
            for key in raw:
                if key[0] == trainer_class:
                    put(key, 4, 2, move)
    for party in parties.values():
        for mon in party:
            mon[2] = [move for move in mon[2] if move != "NO_MOVE"]
