"""Inventaire vérifiable des ressources finales, sans lecture des sources téléchargées."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from string import ascii_lowercase

MANIFEST = "assets.sha256"
_MAX_FILES = 20_000


def _required_paths(assets: Path) -> set[str]:
    """Ressources référencées par la base et variantes utilisées par l'application."""
    database = assets / "database/pokedex.db"
    if not database.is_file():
        raise ValueError(f"Asset indispensable absent : {database}")
    paths = {"database/pokedex.db", "licenses/meteocons.txt"}
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        for (species,) in connection.execute("SELECT id FROM pokemon"):
            for style in ("pokemon", "pokemon/shiny"):
                for variant in ("static", "animated"):
                    paths.add(f"sprites/{style}/{variant}/{species}.webp")
        for (identifier,) in connection.execute("SELECT identifier FROM item WHERE has_sprite = 1"):
            paths.add(f"sprites/items/{identifier}.webp")
        rows = connection.execute(
            """SELECT DISTINCT vg.identifier, o.sprite FROM map_object o JOIN map m ON m.id = o.map_id
               JOIN version_group vg ON vg.id = m.version_group_id WHERE o.sprite IS NOT NULL"""
        )
        paths.update(f"maps/{group}/sprites/{sprite}.webp" for group, sprite in rows)
        rows = connection.execute(
            """SELECT vg.identifier, m.identifier, m.level_count FROM map m
               JOIN version_group vg ON vg.id = m.version_group_id WHERE m.parent_map_id IS NULL"""
        )
        for group, identifier, levels in rows:
            for level in range(levels):
                folder = assets / "maps" / group / identifier / str(level)
                tiles = list(folder.glob("*.webp"))
                if not tiles:
                    raise ValueError(f"Tuiles indispensables absentes : {folder}")
                paths.update(tile.relative_to(assets).as_posix() for tile in tiles)
    for style in ("unown", "unown/shiny"):
        for variant in ("static", "animated"):
            paths.update(
                f"sprites/{style}/{variant}/{form}.webp" for form in (*ascii_lowercase, "exclamation", "question")
            )
    return paths


def write_manifest(assets: Path) -> None:
    """À appeler uniquement après génération et validation des ressources finales."""
    required = _required_paths(assets)
    missing = sorted(path for path in required if not (assets / path).is_file())
    if missing:
        raise ValueError(f"Assets indispensables absents : {missing}")
    files = sorted(path for path in assets.rglob("*") if path.is_file() and path.name != MANIFEST)
    if len(files) > _MAX_FILES:
        raise ValueError(f"Trop d'assets : {len(files)} (maximum {_MAX_FILES})")
    lines: list[str] = []
    for path in files:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        lines.append(f"{digest}  {path.relative_to(assets).as_posix()}")
    (assets / MANIFEST).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def check_manifest(assets: Path) -> None:
    manifest = assets / MANIFEST
    if not manifest.is_file():
        raise ValueError(f"Inventaire des assets absent : {manifest}")
    entries = manifest.read_text("utf-8").splitlines()
    if not entries or len(entries) > _MAX_FILES:
        raise ValueError(f"Inventaire vide ou trop volumineux : {manifest}")
    listed = set()
    for entry in entries:
        digest, separator, relative = entry.partition("  ")
        path = assets / relative
        if not separator or len(digest) != 64 or not path.resolve().is_relative_to(assets.resolve()):
            raise ValueError(f"Entrée d'inventaire invalide : {entry}")
        if relative in listed:
            raise ValueError(f"Asset en double dans l'inventaire : {relative}")
        listed.add(relative)
        if not path.is_file():
            raise ValueError(f"Asset indispensable absent : {path}")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != digest:
            raise ValueError(f"Asset modifié sans mise à jour de l'inventaire : {path}")
    if missing := _required_paths(assets) - listed:
        raise ValueError(f"Assets indispensables absents de l'inventaire : {sorted(missing)}")
