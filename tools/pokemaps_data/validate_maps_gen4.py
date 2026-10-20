"""Validation des catalogues et tuiles DS produits, sans téléchargement ni régénération."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image

from .maps_assembly_coordinates_gen4 import read_coordinates
from .maps_layout import identifier

_MAX_FILES = 30_000


def validate_catalog(output: Path) -> None:
    with (output / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    maps = {row["const"]: row for row in rows}
    if not rows or len(maps) != len(rows) or "SINNOH" not in maps:
        raise ValueError(f"{output} : catalogue vide, doublons ou Sinnoh absent")
    for row in rows:
        _validate_row(output, row, maps)
    _validate_assemblies(output, maps)
    matrices = json.loads((output / "matrices.json").read_text(encoding="utf-8"))
    headers = {header["index"]: header for header in matrices["headers"]}
    for header in headers.values():
        if header["constant"] not in maps:
            raise ValueError(f"{output} : en-tête absent du catalogue : {header['constant']}")
    _validate_passages(output, headers)
    _validate_sprites(output)
    _validate_dynamic_props(output, headers)
    _validate_layers(output, matrices)
    _validate_tiles(output)


def _validate_assemblies(output: Path, maps: dict[str, dict[str, str]]) -> None:
    for const, (native, offset) in read_coordinates(output).items():
        row = maps.get(const)
        if row is None or native not in maps or not row["parent"]:
            raise ValueError(f"{output} : repère d'assemblage sans région ou plan natif : {const}")
        if any(value % 256 for value in offset) or int(row["x"]) < offset[0] or int(row["y"]) < offset[1]:
            raise ValueError(f"{output} : région mal translatée : {const}")


def _validate_row(output: Path, row: dict[str, str], maps: dict[str, dict[str, str]]) -> None:
    const = row["const"]
    if not row["name_fr"].strip() or min(int(row["width"]), int(row["height"])) <= 0:
        raise ValueError(f"{output} : nom ou dimensions invalides : {const}")
    if row["origin"] and row["origin"] not in maps:
        raise ValueError(f"{output} : origine absente : {const} : {row['origin']}")
    if row["parent"]:
        parent = maps.get(row["parent"])
        if parent is None or parent["parent"] or int(row["level_count"]) != 0:
            raise ValueError(f"{output} : parent de carte invalide : {const}")
        for axis, size in (("x", "width"), ("y", "height")):
            if int(row[axis]) < 0 or int(row[axis]) + int(row[size]) > int(parent[size]):
                raise ValueError(f"{output} : région hors de l'assemblage : {const}")
        return
    for level in range(int(row["level_count"])):
        if not any((output / identifier(const) / str(level)).glob("*.webp")):
            raise ValueError(f"{output} : carte sans tuile : {const} niveau {level}")


def _validate_passages(output: Path, headers: dict[int, dict]) -> None:
    with (output / "passages.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    allowed = {"warp", "unused", "dynamic", "script", "elevator", "boat", "fly", "platform", "random_room"}
    for row in rows:
        if row["kind"] not in allowed or not row["evidence"]:
            raise ValueError(f"{output} : liaison inconnue ou sans source : {row}")
        if row["source"] and int(row["source"]) not in headers:
            raise ValueError(f"{output} : départ de liaison absent : {row}")
        if row["target"] and row["kind"] != "unused" and int(row["target"]) not in headers:
            raise ValueError(f"{output} : arrivée de liaison absente : {row}")
        if bool(row["target_x"]) != bool(row["target_z"]):
            raise ValueError(f"{output} : coordonnées d'arrivée incomplètes : {row}")
    if sum(row["kind"] == "fly" for row in rows) != 20 or sum(row["kind"] == "boat" for row in rows) != 8:
        raise ValueError(f"{output} : liaisons de Vol ou de bateau incomplètes")


def _validate_sprites(output: Path) -> None:
    catalog = json.loads((output / "sprites.json").read_text(encoding="utf-8"))
    images = {sprite["graphics"] for sprite in catalog["sprites"]}
    others = {entry["graphics"] for entry in catalog["without_texture"]}
    if images & others:
        raise ValueError(f"{output} : un graphisme est à la fois une image et un modèle")
    events = json.loads((output / "events.json").read_text(encoding="utf-8"))
    used = {obj["graphics"] for event in events.values() for obj in event["object_events"]}
    if used != images | others:
        raise ValueError(f"{output} : graphismes d'événements absents du catalogue")
    for sprite in catalog["sprites"]:
        graphics = sprite["graphics"]
        path = output / "sprites" / f"{graphics}.webp"
        if not path.is_file():
            raise ValueError(f"{output} : image de personnage absente : {graphics}")
        with Image.open(path) as image:
            if list(image.size) != sprite["size"] or image.convert("RGBA").getbbox() is None:
                raise ValueError(f"{path} : dimensions ou image de personnage invalides")


def _validate_tiles(output: Path) -> None:
    files = list(output.rglob("*.webp"))
    if not files or len(files) > _MAX_FILES:
        raise ValueError(f"{output} : nombre de fichiers image invalide : {len(files)}")
    for path in files:
        if path.parent.name.isdecimal():
            with Image.open(path) as tile:
                if tile.size != (256, 256) or tile.format != "WEBP":
                    raise ValueError(f"{path} : tuile WebP 256 × 256 attendue")
                tile.load()


def _validate_dynamic_props(output: Path, headers: dict[int, dict]) -> None:
    catalog = json.loads((output / "dynamic-props.json").read_text(encoding="utf-8"))
    for prop in catalog["props"]:
        if prop["header"] not in headers or not prop["evidence"] or prop["model"] < 0:
            raise ValueError(f"{output} : décor moteur sans en-tête, modèle ou source : {prop}")
        position, rotation = prop["position"], prop["rotation"]
        if (
            len(position) != 3
            or len(rotation) != 3
            or any(type(value) is not int or not -32768 <= value < 32768 for value in position)
            or position[0] < 0
            or position[2] < 0
            or any(type(value) is not int or not 0 <= value < 65536 for value in rotation)
        ):
            raise ValueError(f"{output} : position ou rotation de décor moteur invalide : {prop}")


def write_inventory(output: Path) -> None:
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "assets.sha256")
    if len(files) > _MAX_FILES:
        raise ValueError(f"{output} : inventaire DS trop grand")
    entries = []
    for path in files:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        entries.append(f"{digest}  {path.relative_to(output).as_posix()}")
    (output / "assets.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


def check_inventory(output: Path) -> None:
    manifest = output / "assets.sha256"
    entries = manifest.read_text(encoding="utf-8").splitlines()
    if not entries or len(entries) > _MAX_FILES:
        raise ValueError(f"{output} : inventaire DS vide ou trop grand")
    found = set()
    for entry in entries:
        digest, separator, relative = entry.partition("  ")
        path = output / relative
        if (
            not separator
            or len(digest) != 64
            or relative in found
            or not path.resolve().is_relative_to(output.resolve())
            or not path.is_file()
        ):
            raise ValueError(f"{output} : entrée d'inventaire DS invalide : {entry}")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != digest:
            raise ValueError(f"{path} : ressource DS modifiée sans mise à jour de l'inventaire")
        found.add(relative)
    actual_files = {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() and path != manifest
    }
    if actual_files != found:
        raise ValueError(f"{output} : inventaire DS incomplet ou fichiers supplémentaires")


def _validate_layers(output: Path, matrices: dict) -> None:
    displays = {display["const"]: display for display in matrices["displays"]}
    for display in displays.values():
        if not display["base"]:
            continue
        parent = displays.get(display["base"])
        if parent is None or parent["base"] or parent["bounds"] != display["bounds"] or not display["replacement"]:
            raise ValueError(f"{output} : niveau inférieur mal aligné : {display['const']}")
        for level in range(display["level_count"]):
            if not any((output / identifier(display["const"]) / str(level)).glob("*.webp")):
                raise ValueError(f"{output} : niveau inférieur vide : {display['const']} zoom {level}")
