"""Équipes des dresseurs de la 2e génération (data/trainers/parties.asm).

Chaque classe a un groupe d'équipes (TrainerGroups, data/trainers/party_pointers.asm), dans l'ordre des classes
de constants/trainer_constants.asm ; l'équipe n de la classe est celle du n-ième dresseur de la classe. Une
équipe commence par « db "NOM@", TRAINERTYPE_… » et finit par « db -1 ». Selon le type, chaque Pokémon est
« niveau, espèce », suivi de l'objet tenu (ITEM) et/ou de ses 4 attaques (MOVES).

Sans attaques écrites, le Pokémon connaît les 4 dernières attaques apprises jusqu'à son niveau (FillMoves,
engine/pokemon/evolve.asm), comme en 1re génération.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pret_models import TrainerPokemon
from .pret_source import macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo

# Arguments qui suivent « niveau, espèce » selon le type d'équipe : objet tenu, puis attaques.
_TRAINER_TYPES = {
    "TRAINERTYPE_NORMAL": (False, False),
    "TRAINERTYPE_ITEM": (True, False),
    "TRAINERTYPE_MOVES": (False, True),
    "TRAINERTYPE_ITEM_MOVES": (True, True),
}
_NO_MOVE, _NO_ITEM, _END = "NO_MOVE", "NO_ITEM", "-1"
_MOVE_COUNT = 4


def read_trainer_parties(repo: Gen2PretRepo) -> dict[tuple[str, int], list[TrainerPokemon]]:
    """(classe, rang de l'équipe à partir de 1) -> équipe, attaques comprises."""
    classes = [trainer_class for trainer_class in repo.trainer_ids if trainer_class != "TRAINER_NONE"]
    groups = [
        macro_args(line, "dw")[0]
        for line in source_lines(repo.path("data/trainers/party_pointers.asm"))
        if line.startswith("dw ")
    ]
    by_label = dict(zip(groups, classes, strict=True))
    result: dict[tuple[str, int], list[TrainerPokemon]] = {}
    current: str | None = None
    party: list[TrainerPokemon] | None = None
    shape = (False, False)
    for line in source_lines(repo.path("data/trainers/parties.asm")):
        if line.endswith(":") and line[:-1] in by_label:
            current = by_label[line[:-1]]
        elif current and line.startswith("db "):
            args = macro_args(line, "db")
            if args[0].startswith('"'):
                shape = _shape(args)
                party = result.setdefault((current, _party_count(result, current) + 1), [])
            elif args == [_END]:
                party = None
            elif party is not None:
                party.append(_pokemon(repo, args, shape))
            else:
                raise ValueError(f"parties.asm : Pokémon hors d'une équipe : {line}")
    return result


def _shape(args: list[str]) -> tuple[bool, bool]:
    if len(args) != 2 or args[1] not in _TRAINER_TYPES:
        raise ValueError(f"parties.asm : en-tête d'équipe illisible : {args}")
    return _TRAINER_TYPES[args[1]]


def _party_count(result: dict[tuple[str, int], list[TrainerPokemon]], trainer_class: str) -> int:
    return sum(1 for key in result if key[0] == trainer_class)


def _pokemon(repo: Gen2PretRepo, args: list[str], shape: tuple[bool, bool]) -> TrainerPokemon:
    has_item, has_moves = shape
    expected = 2 + has_item + _MOVE_COUNT * has_moves
    if len(args) != expected:
        raise ValueError(f"parties.asm : {len(args)} valeurs au lieu de {expected} : {args}")
    level, species = parse_int(args[0]), args[1]
    item = args[2] if has_item and args[2] != _NO_ITEM else None
    if has_moves:
        moves = tuple(move for move in args[2 + has_item :] if move != _NO_MOVE)
    else:
        moves = tuple(default_moves(repo, species, level))
    return TrainerPokemon(species, level, moves, item)


def default_moves(repo: Gen2PretRepo, species: str, level: int) -> list[str]:
    """Attaques d'un Pokémon à ce niveau (FillMoves : les 4 dernières apprises, sans doublon)."""
    if species not in repo.learnsets:
        raise ValueError(f"{repo.root.name} : attaques inconnues pour {species}")
    moves: list[str] = []
    for learn_level, move in repo.learnsets[species]:
        if learn_level > level:
            break
        if move in moves:
            continue
        if len(moves) == _MOVE_COUNT:
            moves.pop(0)
        moves.append(move)
    return moves
