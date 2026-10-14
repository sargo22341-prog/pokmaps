"""Combats contre le rival de Rouge, Bleu et Jaune : équipe fixe, ou une équipe par variante de la partie.

Le script de chaque combat écrit le numéro d'équipe dans wTrainerNo :
- un nombre fixe (« ld a, 2 ») ;
- Rouge et Bleu : selon wRivalStarter, le Pokémon de départ du rival, par une suite de « cp STARTERn » et
  « ld a, numéro » (le dernier numéro vaut pour le Pokémon restant) ou par une table « db STARTERn, numéro » ;
- Jaune : wRivalStarter plus un décalage (« add 7 »), wRivalStarter valant RIVAL_STARTER_JOLTEON, _FLAREON ou
  _VAPOREON selon les deux premiers combats.

Rouge et Bleu nomment la variante par le Pokémon de départ du joueur, dont le rival prend toujours le
contre (scripts/OaksLab.asm) ; Jaune par l'évolution finale de l'Évoli du rival.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_models import TrainerVariant, VariantKind
from .pret_source import parse_int, source_lines

_RIVAL_BATTLE = re.compile(r"ld a, (OPP_RIVAL[123])\nld \[wCurOpponent\], a\n")
_SELECTION_END = re.compile(r"ld \[wTrainerNo\], a|call Route22GetRivalTrainerNoByStarterScript")
_FIXED = re.compile(r"ld a, (\$?[\dA-Fa-f]+)\nld \[wTrainerNo\], a")
_OFFSET = re.compile(r"ld a, \[wRivalStarter\]\nadd (\$?[\dA-Fa-f]+)\nld \[wTrainerNo\], a")
_STARTER_EQU = re.compile(r"DEF (STARTER\d|RIVAL_STARTER_\w+)\s+EQU (\w+)")
_CHAMPION_SHARED_MOVE = re.compile(r"ld a, ([A-Z][A-Z_]+)\nld \[wEnemyMon(\d)Moves \+ 2\], a")
_CHAMPION_STARTER_MOVE = re.compile(r"cp (STARTER\d)\nld b, (\w+)\njr z, \.GiveStarterMove")
_CHAMPION_DEFAULT_MOVE = re.compile(r"ld b, (\w+)\n\.GiveStarterMove\nld a, b\nld \[wEnemyMon(\d)Moves \+ 2\], a")
_STARTER_CHOICE = re.compile(
    r"ld a, (STARTER\d)\nld \[wRivalStarterTemp\], a\nld a, \w+\nld \[wRivalStarterBallSpriteIndex\], a\n"
    r"ld a, (STARTER\d)\n"
)


@dataclass(frozen=True)
class RivalBattle:
    trainer_class: str  # ex. OPP_RIVAL1
    number: int | None  # équipe fixe, None si elle dépend de la partie
    variants: tuple[TrainerVariant, ...] = ()

    def __post_init__(self) -> None:
        if (self.number is None) == (not self.variants):
            raise ValueError(f"{self.trainer_class} : ni équipe fixe ni variantes, ou les deux")


def rival_battles(root: Path, script: str) -> list[RivalBattle]:
    """Combats contre le rival du script `script` (texte sans commentaires, une instruction par ligne)."""
    starters = _starter_constants(root)
    battles = []
    for match in _RIVAL_BATTLE.finditer(script):
        end = _SELECTION_END.search(script, match.end())
        if end is None:
            raise ValueError(f"Combat {match.group(1)} sans choix d'équipe")
        segment = script[match.end() : end.end()]
        battles.append(_battle(root, starters, match.group(1), segment, script[end.end() :]))
    return battles


def script_text(path: Path) -> str:
    """Instructions d'un script, une par ligne, sans commentaires ni indentation."""
    return "\n".join(source_lines(path)) + "\n"


def _battle(root: Path, starters: dict[str, str], trainer_class: str, segment: str, rest: str) -> RivalBattle:
    if fixed := _FIXED.fullmatch(segment):
        return RivalBattle(trainer_class, parse_int(fixed.group(1)))
    if offset := _OFFSET.search(segment):
        variants = tuple(
            TrainerVariant(
                VariantKind.RIVAL_EVOLUTION,
                name.removeprefix("RIVAL_STARTER_"),
                parse_int(value) + parse_int(offset.group(1)),
            )
            for name, value in sorted(starters.items(), key=lambda item: item[1])
            if name.startswith("RIVAL_STARTER_")
        )
        return RivalBattle(trainer_class, None, variants)
    by_rival_starter = _table_choice(rest) if "Route22GetRivalTrainerNoByStarterScript" in segment else None
    by_rival_starter = by_rival_starter or _compare_choice(segment, starters)
    player_of = _player_starters(root)
    variants = tuple(
        TrainerVariant(VariantKind.PLAYER_STARTER, starters[player_of[rival]], number)
        for rival, number in sorted(by_rival_starter.items(), key=lambda item: item[1])
    )
    return RivalBattle(trainer_class, None, variants)


def _table_choice(rest: str) -> dict[str, int]:
    """Table « .StarterTable: » qui suit le combat : « db STARTERn, numéro »."""
    table = rest[rest.index(".StarterTable:\n") :].splitlines()[1:]
    rows = [re.fullmatch(r"db (STARTER\d), (\$?[\dA-Fa-f]+)", line) for line in table]
    pairs = [row for row in rows[: next((i for i, row in enumerate(rows) if row is None), len(rows))] if row]
    return {row.group(1): parse_int(row.group(2)) for row in pairs}


def _compare_choice(segment: str, starters: dict[str, str]) -> dict[str, int]:
    """« cp STARTERn » puis « ld a, numéro » ; le dernier numéro, sans comparaison, vaut pour le Pokémon restant."""
    result: dict[str, int] = {}
    pending: str | None = None
    default: int | None = None
    for line in segment.splitlines():
        if compare := re.fullmatch(r"cp (STARTER\d)", line):
            pending = compare.group(1)
        elif number := re.fullmatch(r"ld a, (\$?[\dA-Fa-f]+)", line):
            if pending is None:
                default = parse_int(number.group(1))
            else:
                result[pending] = parse_int(number.group(1))
            pending = None
    remaining = sorted(name for name in starters if name.startswith("STARTER") and name not in result)
    if default is None or len(result) != 2 or len(remaining) != 1:
        raise ValueError(f"Choix de l'équipe du rival illisible : {segment!r}")
    return result | {remaining[0]: default}


def _starter_constants(root: Path) -> dict[str, str]:
    """STARTERn -> espèce (Rouge, Bleu) et RIVAL_STARTER_X -> valeur de wRivalStarter (Jaune)."""
    text = (root / "constants/pokemon_constants.asm").read_text("utf-8")
    return dict(_STARTER_EQU.findall(text))


def _player_starters(root: Path) -> dict[str, str]:
    """Pokémon de départ du rival -> celui du joueur, d'après les Poké Balls du laboratoire."""
    pairs = _STARTER_CHOICE.findall(script_text(root / "scripts/OaksLab.asm"))
    if len(pairs) != len({rival for rival, _ in pairs}) or len(pairs) != 3:
        raise ValueError(f"scripts/OaksLab.asm : choix du rival illisibles : {pairs}")
    return dict(pairs)


def champion_moves(root: Path) -> dict[int, list[tuple[int, str]]]:
    """Rouge et Bleu : équipe RIVAL3 -> (rang du Pokémon à partir de 0, attaque) que ReadTrainer écrit en 3e
    attaque (.ChampionRival : Piqué au premier, puis une attaque selon le Pokémon de départ du rival au dernier)."""
    lines = source_lines(root / "engine/battle/read_trainer_party.asm")
    if ".ChampionRival" not in lines:
        return {}
    body = "\n".join(lines[lines.index(".ChampionRival") : lines.index(".FinishUp")]) + "\n"
    shared = [(int(mon) - 1, move) for move, mon in _CHAMPION_SHARED_MOVE.findall(body)]
    starter_move = _CHAMPION_DEFAULT_MOVE.search(body)
    by_starter = dict(_CHAMPION_STARTER_MOVE.findall(body))
    script = script_text(root / "scripts/ChampionsRoom.asm")
    battles = [choice for trainer_class, choice in _rival_choices(root, script) if trainer_class == "OPP_RIVAL3"]
    if len(shared) != 1 or starter_move is None or len(by_starter) != 2 or len(battles) != 1:
        raise ValueError("engine/battle/read_trainer_party.asm : attaques du Maître illisibles")
    mon = int(starter_move.group(2)) - 1
    return {
        number: [*shared, (mon, by_starter.get(rival_starter, starter_move.group(1)))]
        for rival_starter, number in battles[0].items()
    }


def _rival_choices(root: Path, script: str) -> list[tuple[str, dict[str, int]]]:
    """Combats dont l'équipe dépend du Pokémon de départ du rival (Rouge, Bleu) : classe et numéros d'équipe."""
    starters = _starter_constants(root)
    result = []
    for match in _RIVAL_BATTLE.finditer(script):
        end = _SELECTION_END.search(script, match.end())
        if end is not None and "cp STARTER" in script[match.end() : end.end()]:
            result.append((match.group(1), _compare_choice(script[match.end() : end.end()], starters)))
    return result
