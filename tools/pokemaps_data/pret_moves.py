"""Effets des attaques, lus dans les désassemblages pret.

data/moves/moves.asm donne, pour chaque attaque, la constante de son effet (BURN_SIDE_EFFECT1 en 1re génération,
EFFECT_BURN_HIT en 2e) : c'est elle que le moteur de combat exécute. Le texte français de chaque effet est relu à
la main dans tools/data/move_effects.csv, une ligne par format de sources pret.

La probabilité d'un effet secondaire vient :
- en 1re génération, de move_effects.csv, relue dans engine/battle/effects.asm (elle dépend de l'effet) ;
- en 2e génération, de moves.asm (elle dépend de l'attaque), écrite en pourcentage et assemblée en
  « n * 255 / 100 » sur 256. Elle n'est lue par le moteur que si le script de l'effet (data/moves/effects.asm)
  appelle effectchance ou tristatuschance : sinon le nombre écrit dans moves.asm ne sert pas.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .games import PretFormat
from .pret_source import macro_args, source_lines
from .sources import DATA_DIR

MOVES_FILE = "data/moves/moves.asm"
# Le moteur tire un nombre de 0 à 255 : un effet a « chance_256 » chances sur 256 de se produire.
RANDOM_RANGE = 256
# Commandes des scripts d'effet de la 2e génération qui tirent la probabilité de l'attaque.
_CHANCE_COMMANDS = frozenset({"effectchance", "tristatuschance"})
_LABEL = re.compile(r"^(\w+):$")


@dataclass(frozen=True)
class PretMove:
    const: str  # constante pret de l'attaque (ex. FIRE_PUNCH)
    effect: str  # constante de son effet (ex. BURN_SIDE_EFFECT1)
    # Probabilité de l'effet sur 256 lue dans moves.asm (2e génération) ; None si elle vient de move_effects.csv
    # (1re génération) ou si l'effet se produit à chaque fois.
    chance_256: int | None = None


@dataclass(frozen=True)
class GameMoves:
    """Attaques d'un jeu, avec le format de ses sources (qui choisit les lignes de move_effects.csv)."""

    pret_format: PretFormat
    moves: list[PretMove]


@dataclass(frozen=True)
class MoveEffect:
    description_fr: str
    # Probabilité de l'effet en %, None s'il se produit à chaque fois.
    chance: float | None


def read_pret_moves(root: Path, pret_format: PretFormat) -> list[PretMove]:
    """Attaques du jeu dans l'ordre de moves.asm, avec la constante de leur effet."""
    moves = [macro_args(line, "move") for line in source_lines(root / MOVES_FILE) if line.startswith("move ")]
    if not moves:
        raise ValueError(f"Aucune attaque lue dans {root / MOVES_FILE}")
    match pret_format:
        case PretFormat.GEN1:
            return [PretMove(args[0], args[1]) for args in moves]
        case PretFormat.GEN2:
            chance_effects = _chance_effects(root)
            return [_gen2_move(args, chance_effects) for args in moves]


def _gen2_move(args: list[str], chance_effects: frozenset[str]) -> PretMove:
    """« move NOM, EFFET, puissance, type, précision, PP, probabilité en % »."""
    const, effect, percent = args[0], args[1], int(args[6])
    if not 0 <= percent <= 100:
        raise ValueError(f"{MOVES_FILE} : probabilité invalide pour {const} : {percent} %")
    if percent == 0 or effect not in chance_effects:
        return PretMove(const, effect)
    return PretMove(const, effect, percent * 255 // 100)


def _chance_effects(root: Path) -> frozenset[str]:
    """Effets (EFFECT_…) dont le script appelle effectchance ou tristatuschance."""
    effects = [
        line.split()[1]
        for line in source_lines(root / "constants/move_effect_constants.asm")
        if line.startswith("const ")
    ]
    pointers = [
        macro_args(line, "dw")[0]
        for line in source_lines(root / "data/moves/effects_pointers.asm")
        if line.startswith("dw ")
    ]
    if len(effects) != len(pointers):
        raise ValueError(f"{root.name} : {len(pointers)} scripts d'effet pour {len(effects)} constantes EFFECT_")
    bodies: dict[str, set[str]] = {}
    current: set[str] = set()
    for line in source_lines(root / "data/moves/effects.asm"):
        if match := _LABEL.match(line):
            current = bodies.setdefault(match.group(1), set())
        else:
            current.add(line.split()[0])
    return frozenset(
        effect for effect, label in zip(effects, pointers, strict=True) if bodies.get(label, set()) & _CHANCE_COMMANDS
    )


@dataclass(frozen=True)
class _EffectRow:
    pret_format: PretFormat
    effect: str
    move: str | None
    chance_256: int | None
    description_fr: str


def _read_effect_rows() -> list[_EffectRow]:
    rows = []
    formats = {pret_format.value: pret_format for pret_format in PretFormat}
    with (DATA_DIR / "move_effects.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            where = f"move_effects.csv : {row['format']} {row['effect']} {row['move']}".rstrip()
            if row["format"] not in formats:
                raise ValueError(f"{where} : format inconnu")
            pret_format = formats[row["format"]]
            chance = int(row["chance_256"]) if row["chance_256"] else None
            if chance is not None and not 0 < chance < RANDOM_RANGE:
                raise ValueError(f"{where} : probabilité invalide : {chance}")
            if chance is not None and pret_format is not PretFormat.GEN1:
                raise ValueError(f"{where} : la probabilité de ce format se lit dans {MOVES_FILE}")
            if not row["description_fr"].strip():
                raise ValueError(f"{where} : description vide")
            description = row["description_fr"].strip()
            rows.append(_EffectRow(pret_format, row["effect"], row["move"] or None, chance, description))
    return rows


def move_effects(games: dict[str, GameMoves]) -> dict[str, dict[str, MoveEffect]]:
    """Effet de chaque attaque de chaque jeu (clé du jeu -> constante pret -> effet) : la ligne propre à
    l'attaque dans move_effects.csv, sinon celle de sa constante d'effet, pour le format du jeu. Une attaque sans
    texte, ou une ligne d'un format construit qui ne sert à aucun jeu, arrête la génération."""
    rows = _read_effect_rows()
    by_move = {(row.pret_format, row.effect, row.move): row for row in rows if row.move}
    by_effect = {(row.pret_format, row.effect): row for row in rows if not row.move}
    result: dict[str, dict[str, MoveEffect]] = {}
    used: set[_EffectRow] = set()
    missing = []
    for game, game_moves in games.items():
        effects = result.setdefault(game, {})
        pret_format = game_moves.pret_format
        for move in game_moves.moves:
            row = by_move.get((pret_format, move.effect, move.const)) or by_effect.get((pret_format, move.effect))
            if row is None:
                missing.append(f"{pret_format.value} {move.const} ({move.effect})")
                continue
            used.add(row)
            chance_256 = move.chance_256 if move.chance_256 is not None else row.chance_256
            chance = None if chance_256 is None else chance_256 * 100 / RANDOM_RANGE
            effects[move.const] = MoveEffect(row.description_fr, chance)
    if missing:
        raise ValueError(f"Effet d'attaque sans texte dans tools/data/move_effects.csv : {sorted(set(missing))}")
    built = {game_moves.pret_format for game_moves in games.values()}
    unused = [
        f"{row.pret_format.value} {row.effect} {row.move or ''}".strip()
        for row in rows
        if row.pret_format in built and row not in used
    ]
    if unused:
        raise ValueError(f"Lignes de tools/data/move_effects.csv sans attaque correspondante : {unused}")
    return result
