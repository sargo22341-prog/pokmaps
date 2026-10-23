"""Non-régression des données et ressources existantes lors de l'ajout de HGSS."""

import hashlib
import sqlite3
from contextlib import closing
from itertools import islice
from pathlib import Path

_ROOTS = frozenset(
    {
        "assets.sha256",
        "database",
        "encounter_backgrounds",
        "hgss.json",
        "hoenn.json",
        "licenses",
        "maps",
        "sinnoh.json",
        "sprites",
    }
)


def validate_destination(previous: Path, candidate: Path) -> None:
    before, target = previous.resolve(), candidate.resolve()
    if candidate.is_symlink() or before.is_relative_to(target) or target.is_relative_to(before):
        raise ValueError("La candidate HGSS doit rester séparée des assets distribués")
    if not candidate.exists():
        return
    entries = list(islice(candidate.iterdir(), len(_ROOTS) + 1))
    if unknown := sorted({path.name for path in entries} - _ROOTS):
        raise ValueError(f"Candidate HGSS : fichiers hors livraison déjà présents : {unknown}")


def qualify(previous: Path, candidate: Path) -> tuple[int, int]:
    if previous.resolve() == candidate.resolve():
        raise ValueError("La comparaison candidate exige deux dossiers distincts")
    with (
        closing(sqlite3.connect(previous / "database/pokedex.db")) as before,
        closing(sqlite3.connect(candidate / "database/pokedex.db")) as after,
    ):
        rows = _compare_tables(before, after)
    files = _compare_files(previous, candidate)
    print(f"HGSS : non-régression vérifiée, {rows} lignes et {files} fichiers antérieurs identiques", flush=True)
    return rows, files


def _compare_tables(before: sqlite3.Connection, after: sqlite3.Connection) -> int:
    tables = [r[0] for r in before.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    count = 0
    if len(tables) > 100:
        raise ValueError("HGSS : trop de tables dans la base précédente")
    for table in tables:
        columns = before.execute(f"PRAGMA table_info({table})").fetchall()
        key_columns = [r[0] for r in sorted(columns, key=lambda r: r[5]) if r[5]]
        if not key_columns:
            raise ValueError(f"HGSS : table sans clé primaire : {table}")
        current = {tuple(row[i] for i in key_columns): row for row in after.execute(f"SELECT * FROM {table}")}
        for row in before.execute(f"SELECT * FROM {table}"):
            key = tuple(row[i] for i in key_columns)
            if current.get(key) != row:
                raise ValueError(f"HGSS : donnée antérieure modifiée : {table} {key}")
            count += 1
    return count


def _compare_files(previous: Path, candidate: Path) -> int:
    lines = (previous / "assets.sha256").read_text(encoding="utf-8").splitlines()
    if not 1 <= len(lines) <= 60_000:
        raise ValueError("HGSS : inventaire de référence vide ou trop grand")
    count = 0
    for line in lines:
        expected, name = line.split("  ", 1)
        if name == "database/pokedex.db":
            continue
        path = candidate / name
        if not path.resolve().is_relative_to(candidate.resolve()):
            raise ValueError(f"HGSS : chemin de référence hors candidate : {name}")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"HGSS : ressource antérieure modifiée : {name}")
        count += 1
    return count
