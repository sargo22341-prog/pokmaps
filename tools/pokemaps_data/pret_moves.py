"""Effets des attaques de la 1re génération, lus dans les désassemblages pret.

data/moves/moves.asm donne, pour chaque attaque, la constante de son effet (BURN_SIDE_EFFECT1,
SLEEP_EFFECT…) : c'est elle que le moteur de combat exécute. Le texte français et la probabilité de
chaque effet sont relus à la main dans tools/data/move_effects.csv, d'après engine/battle/effects.asm.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .pret_source import macro_args, source_lines
from .sources import DATA_DIR

MOVES_FILE = "data/moves/moves.asm"
# Le moteur tire un nombre de 0 à 255 : un effet a « chance_256 » chances sur 256 de se produire.
RANDOM_RANGE = 256


@dataclass(frozen=True)
class PretMove:
    const: str  # constante pret de l'attaque (ex. FIRE_PUNCH)
    effect: str  # constante de son effet (ex. BURN_SIDE_EFFECT1)


@dataclass(frozen=True)
class MoveEffect:
    description_fr: str
    # Probabilité de l'effet en %, None s'il se produit à chaque fois.
    chance: float | None


def read_pret_moves(root: Path) -> list[PretMove]:
    """Attaques du jeu dans l'ordre de moves.asm, avec la constante de leur effet."""
    moves = [macro_args(line, "move") for line in source_lines(root / MOVES_FILE) if line.startswith("move ")]
    if not moves:
        raise ValueError(f"Aucune attaque lue dans {root / MOVES_FILE}")
    return [PretMove(args[0], args[1]) for args in moves]


@dataclass(frozen=True)
class _EffectRow:
    effect: str
    move: str | None
    chance_256: int | None
    description_fr: str


def _read_effect_rows() -> list[_EffectRow]:
    rows = []
    with (DATA_DIR / "move_effects.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            chance = int(row["chance_256"]) if row["chance_256"] else None
            if chance is not None and not 0 < chance < RANDOM_RANGE:
                raise ValueError(f"move_effects.csv : probabilité invalide pour {row['effect']} : {chance}")
            if not row["description_fr"].strip():
                raise ValueError(f"move_effects.csv : description vide pour {row['effect']} {row['move']}")
            rows.append(_EffectRow(row["effect"], row["move"] or None, chance, row["description_fr"].strip()))
    return rows


def move_effects(games: dict[str, list[PretMove]]) -> dict[str, dict[str, MoveEffect]]:
    """Effet de chaque attaque de chaque jeu (clé du jeu -> constante pret -> effet) : la ligne propre à
    l'attaque dans move_effects.csv, sinon celle de sa constante d'effet. Une attaque sans texte, ou une
    ligne qui ne sert à aucun jeu, arrête la génération."""
    rows = _read_effect_rows()
    by_move = {(row.effect, row.move): row for row in rows if row.move}
    by_effect = {row.effect: row for row in rows if not row.move}
    result: dict[str, dict[str, MoveEffect]] = {}
    used: set[_EffectRow] = set()
    missing = []
    for game, moves in games.items():
        effects = result.setdefault(game, {})
        for move in moves:
            row = by_move.get((move.effect, move.const)) or by_effect.get(move.effect)
            if row is None:
                missing.append(f"{move.const} ({move.effect})")
                continue
            used.add(row)
            chance = None if row.chance_256 is None else row.chance_256 * 100 / RANDOM_RANGE
            effects[move.const] = MoveEffect(row.description_fr, chance)
    if missing:
        raise ValueError(f"Effet d'attaque sans texte dans tools/data/move_effects.csv : {sorted(set(missing))}")
    unused = [f"{row.effect} {row.move or ''}".strip() for row in rows if row not in used]
    if unused:
        raise ValueError(f"Lignes de tools/data/move_effects.csv sans attaque correspondante : {unused}")
    return result
