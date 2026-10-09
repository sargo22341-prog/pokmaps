"""Effets et probabilités en pourcentage des attaques du moteur GBA."""

from __future__ import annotations

from pathlib import Path

from .pret_gen3_source import read_initializers
from .pret_moves import PretMove


def read_moves(root: Path) -> list[PretMove]:
    path = root / "src/data/battle_moves.h"
    if not path.is_file():
        path = root / "src/data/battle_moves.c"
    entries = read_initializers(path, "MOVE_", frozenset({"ENGLISH"}))
    result = []
    for name, fields in entries.items():
        allowed = {"effect", "power", "type", "accuracy", "pp", "secondaryEffectChance", "target", "priority", "flags"}
        if unknown := fields.keys() - allowed:
            raise ValueError(f"{path} : champs d’attaque inconnus pour {name} : {sorted(unknown)}")
        effect = fields.get("effect", "")
        if not effect.startswith("EFFECT_") or "secondaryEffectChance" not in fields:
            raise ValueError(f"{path} : effet absent pour {name}")
        try:
            chance = int(fields["secondaryEffectChance"])
        except ValueError as error:
            raise ValueError(f"{path} : probabilité non entière pour {name}") from error
        if not 0 <= chance <= 100:
            raise ValueError(f"{path} : probabilité invalide pour {name} : {chance}")
        if name != "MOVE_NONE":
            result.append(
                PretMove(name.removeprefix("MOVE_"), effect, chance_percent=chance if 0 < chance < 100 else None)
            )
    return result
