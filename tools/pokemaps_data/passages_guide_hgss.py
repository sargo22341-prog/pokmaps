"""Liaisons du guide HGSS : variantes de scénario écartées et accès scriptés attestés."""

import csv
from pathlib import Path

from .maps import WarpRow
from .maps_characters_hgss import project
from .maps_layout import identifier
from .pret_gen4_source import read_text
from .pret_hgss_maps import HgssMapRepo
from .sources import DATA_DIR


def excluded_passages(catalog: dict) -> set[tuple[int, int]]:
    known = {(p["source"], p["index"]) for p in catalog["passages"]}
    result = set()
    for row in _rows("hgss_guide_passages.csv", ("source", "index", "reason")):
        key = int(row["source"]), int(row["index"])
        if key not in known or key in result or not row["reason"].strip():
            raise ValueError(f"HGSS : exclusion de passage invalide : {row}")
        result.add(key)
    return result


def script_passages(root: Path, maps: dict, offsets: dict) -> list[WarpRow]:
    repo = HgssMapRepo(root, "heartgold")
    result = []
    columns = ("source", "x", "z", "destination", "target_x", "target_z", "file", "instruction", "reason")
    rows = _rows("hgss_script_passages.csv", columns)
    for row in rows:
        source, target = maps[int(row["source"])], maps[int(row["destination"])]
        path = root / row["file"]
        if not path.resolve().is_relative_to(root.resolve()) or not row["reason"]:
            raise ValueError(f"HGSS : provenance de passage invalide : {row}")
        instructions = {" ".join(line.split()) for line in read_text(path).splitlines()}
        if row["instruction"] not in instructions:
            raise ValueError(f"HGSS : instruction de passage absente : {row['instruction']}")
        start = _point(repo, source, int(row["x"]), int(row["z"]), offsets)
        end = _point(repo, target, int(row["target_x"]), int(row["target_z"]), offsets)
        result.append(WarpRow(source["const"], *start, target["const"], *end))
    if len(set((w.map_const, w.x, w.y) for w in result)) != len(result):
        raise ValueError("HGSS : passages scriptés répétés")
    return result


def _point(repo: HgssMapRepo, record: dict, x: int, z: int, offsets: dict) -> tuple[int, int]:
    px, py = project(repo, record, dict(x=x, z=z))
    dx, dy = offsets[identifier(record["const"])]
    return px + dx, py + dy


def _rows(name: str, columns: tuple[str, ...]) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if path.stat().st_size > 64 * 1024:
        raise ValueError(f"{path} : corrections de passages trop volumineuses")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(columns):
            raise ValueError(f"{path} : colonnes de passages invalides")
        rows = list(reader)
    if not 1 <= len(rows) <= 64 or any(set(row) != set(columns) or None in row.values() for row in rows):
        raise ValueError(f"{path} : lignes de passages invalides")
    return rows
