"""Validation hors ligne des catalogues de personnages des jeux Hoenn activés."""

from __future__ import annotations

from pathlib import Path

from .games import EMERALD, RUBY_SAPPHIRE, Game
from .pret_gen3_source import read_json
from .sources import PRET_COMMITS


def validate_character_catalog(folder: Path, game: Game) -> None:
    if game not in (RUBY_SAPPHIRE, EMERALD):
        raise ValueError(f"{folder} : catalogue de personnages hors Hoenn")
    data = read_json(folder / "characters.json")
    versions = {version for version, _ in game.pret_versions}
    if data.get("schema") != 1 or data.get("commit") != PRET_COMMITS[game.pret_repo]:
        raise ValueError(f"{folder} : version ou source du catalogue de personnages invalide")
    rows = data.get("characters")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10_000:
        raise ValueError(f"{folder} : personnages absents ou trop nombreux")
    keys: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.get("version"), row.get("map_const"), row.get("key"))
        if key[0] not in versions or not all(isinstance(part, str) and part for part in key[1:]) or key in keys:
            raise ValueError(f"{folder} : personnage répété ou version invalide : {key}")
        keys.add(key)
        event, result = row.get("event", {}), row.get("result", {})
        if any(not isinstance(event.get(axis), int) or event[axis] < 0 for axis in ("x", "y")):
            raise ValueError(f"{folder} : coordonnées de personnage invalides : {key}")
        if not all(isinstance(result.get(field), list) for field in ("offers", "trainers", "flags", "specials")):
            raise ValueError(f"{folder} : script de personnage incomplet : {key}")
    if {version for version, _, _ in keys} != versions:
        raise ValueError(f"{folder} : personnages d'une version absents")
    _validate_scenes(data.get("scenes"), versions, folder)
    if not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError(f"{folder} : objets fixes absents du catalogue")


def _validate_scenes(rows: object, versions: set[str], folder: Path) -> None:
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10_000:
        raise ValueError(f"{folder} : scènes absentes ou trop nombreuses")
    for row in rows:
        if (
            row.get("version") not in versions
            or not str(row.get("value", "")).isdecimal()
            or not all(row.get(field) for field in ("variable", "script", "table"))
            or not isinstance(row.get("conditions"), list)
        ):
            raise ValueError(f"{folder} : condition de scène invalide : {row}")
