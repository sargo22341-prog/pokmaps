"""Caractéristiques et classe par attaque des deux formats DS, sans interprétation des effets."""

from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_source import read_json


@dataclass(frozen=True)
class DsMove:
    identifier: str
    power: int
    pp: int
    accuracy: int
    type: str
    damage_class: str


def read_ds_moves(root: Path, repo: str) -> tuple[DsMove, ...]:
    if repo == "pokeplatinum":
        paths = sorted((root / "res/moves").glob("*/data.json"))
        if not 467 <= len(paths) <= 468:
            raise ValueError(f"{root} : nombre d'attaques DS invalide : {len(paths)}")
        rows = [(p.parent.name, read_json(p)) for p in paths if p.parent.name != "none"]
    elif repo == "pokediamond":
        data = read_json(root / "files/poketool/waza/waza_tbl.json")["waza_tbl"]
        # Trois entrées techniques (468–470) suivent les attaques jouables dans Diamant/Perle.
        reserved = {"MOVE_NONE", "MOVE_468", "MOVE_469", "MOVE_470"}
        rows = [(r["name"].removeprefix("MOVE_").lower(), r) for r in data if r["name"] not in reserved]
    else:
        raise ValueError(f"Dépôt d'attaques DS inconnu : {repo}")
    result = []
    classes = {"CLASS_PHYSICAL": "physical", "CLASS_SPECIAL": "special", "CLASS_STATUS": "status"}
    for name, row in rows:
        if not 0 <= row["power"] <= 255 or not 1 <= row["pp"] <= 40 or not 0 <= row["accuracy"] <= 100:
            raise ValueError(f"{root} : caractéristiques invalides pour {name}")
        type_name = row["type"].removeprefix("TYPE_").lower()
        type_name = {"mystery": "unknown", "curse": "unknown"}.get(type_name, type_name)
        result.append(
            DsMove(name.replace("_", "-"), row["power"], row["pp"], row["accuracy"], type_name, classes[row["class"]])
        )
    if len(result) != 467 or len({r.identifier for r in result}) != 467:
        raise ValueError(f"{root} : 467 attaques uniques attendues")
    return tuple(result)
