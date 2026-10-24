"""Préparation, export et validation des ressources HGSS distribuables."""

import hashlib
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

from .guide_resources_hgss import build_resources
from .placement_hgss import read_placement_json
from .preview_characters_hgss import build_characters, check_characters
from .preview_content_hgss import build_content, check_content
from .preview_maps_hgss import build_hgss_maps
from .preview_placement_hgss import build_placement, check_placement
from .preview_pokemon_hgss import build_hgss_pokemon
from .preview_wild_hgss import build_hgss_encounters, check_encounters_preview
from .sources import HGSS_PRET_COMMIT, PREVIEW_DIR
from .validate_content_hgss import validate_content
from .validate_johto_hgss import check_johto_preview
from .validate_maps_gen4 import check_inventory


def prepare(cache: Path, assets: Path, workers: int) -> None:
    from .preview_pokemon_hgss import validate_sources
    from .sources import fetch_pokeapi_csv
    from .sources_atlas_hgss import validate_atlas_sources
    from .sources_characters_hgss import validate_character_sources

    validate_sources(cache / "hgss-qualification", fetch_pokeapi_csv(cache))
    validate_atlas_sources(cache / "hgss-qualification")
    validate_character_sources(cache / "hgss-qualification")
    tasks = (
        (
            "cartes",
            lambda: check_johto_preview(PREVIEW_DIR / "hgss-maps"),
            lambda: build_hgss_maps(cache, PREVIEW_DIR, workers),
        ),
        ("Pokémon", _check_pokemon, lambda: build_hgss_pokemon(cache, PREVIEW_DIR, assets)),
        (
            "rencontres",
            lambda: check_encounters_preview(PREVIEW_DIR / "hgss-encounters"),
            lambda: build_hgss_encounters(cache, PREVIEW_DIR, assets),
        ),
        (
            "placement",
            lambda: check_placement(PREVIEW_DIR / "hgss-placement"),
            lambda: build_placement(cache, PREVIEW_DIR),
        ),
        (
            "personnages",
            lambda: check_characters(PREVIEW_DIR / "hgss-characters"),
            lambda: build_characters(cache, PREVIEW_DIR),
        ),
        ("contenus", lambda: check_content(PREVIEW_DIR / "hgss-content"), lambda: build_content(cache, PREVIEW_DIR)),
    )
    for name, check, build in tasks:
        _ensure(name, check, build)


def _ensure(name: str, check: Callable[[], object], build: Callable[[], None]) -> None:
    try:
        check()
    except (OSError, ValueError) as error:
        print(f"HGSS : reconstruction des {name} : {error}", flush=True)
        build()
        check()


def _check_pokemon() -> None:
    folder = PREVIEW_DIR / "hgss-pokemon"
    inventory = read_placement_json(folder / "inventory.json")
    if not inventory or len(inventory) > 5000:
        raise ValueError("HGSS : inventaire Pokémon vide ou trop grand")
    for name, expected in inventory.items():
        path = folder / name
        if (
            not path.resolve().is_relative_to(folder.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"HGSS : asset Pokémon périmé : {name}")


def build_catalog(assets: Path, resources: Path) -> None:
    content = read_placement_json(PREVIEW_DIR / "hgss-content/content.json")
    validate_content(content)
    content["application_recipe"] = export_recipe()
    (assets / "hgss.json").write_text(json.dumps(content, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    build_resources(content, resources)


def validate_assets(assets: Path) -> None:
    content = read_placement_json(assets / "hgss.json")
    validate_content(content)
    if content.get("application_recipe") != export_recipe():
        raise ValueError("HGSS : recette de distribution périmée, régénérer les assets")
    folder = assets / "maps/heartgold-soulsilver"
    check_inventory(folder)
    data = read_placement_json(folder / "catalog.json")
    source = data["source_catalog"]
    lower = sum(
        max(len(r["layers"]) for r in source["maps"] if r["plan"] == p["id"])
        for p in source["plans"]
        if p["id"] not in {"johto-exterieurs", "kanto-exterieurs"}
    )
    from .safari_atlas_hgss import validate_atlas

    validate_atlas(assets)
    expected = 497 + sum(not p.get("standalone", False) for p in source["plans"]) + lower
    if data["commit"] != HGSS_PRET_COMMIT or len(data["maps"]) != expected:
        raise ValueError("HGSS : catalogue distribué incomplet ou d'un autre commit")
    constants = {row["const"] for row in data["maps"]}
    numbers = {row["number"] for row in data["maps"]}
    if len(constants) != expected or len(numbers) != expected:
        raise ValueError("HGSS : cartes distribuées répétées")
    for row in data["maps"]:
        name = row["const"].removeprefix("MAP_").lower().replace("_", "-")
        if row["parent"] is not None:
            if row["parent"] not in constants:
                raise ValueError(f"HGSS : parent absent : {name}")
            continue
        for level in range(row["level_count"]):
            if not any((folder / name / str(level)).glob("*.webp")):
                raise ValueError(f"HGSS : tuiles absentes : {name}, niveau {level}")


def validate_database(connection: sqlite3.Connection) -> list[str]:
    if connection.execute("SELECT count(*) FROM version_group WHERE id = 10").fetchone()[0] == 0:
        return []
    checks = (
        ("deux versions HGSS", "SELECT count(*) FROM version WHERE version_group_id=10", 2),
        ("profils des 493 espèces HGSS", "SELECT count(*) FROM pokemon_version_group WHERE version_group_id=10", 493),
        ("régional HGSS de 256 espèces", "SELECT count(*) FROM pokedex_entry WHERE pokedex_id=7", 256),
    )
    errors = [
        f"HGSS : {label} incomplets"
        for label, query, expected in checks
        if connection.execute(query).fetchone()[0] != expected
    ]
    errors.extend(_validate_map_placement(connection))
    errors.extend(_validate_fixed_legends(connection))
    return errors


def _validate_fixed_legends(connection: sqlite3.Connection) -> list[str]:
    errors = []
    for species, place in ((249, "whirl-islands-b3f-lugia-cave"), (250, "bell-tower-roof")):
        for version in (15, 16):
            rows = connection.execute(
                """SELECT m.identifier FROM map_object o JOIN map m ON m.id=o.map_id
                   WHERE m.version_group_id=10 AND o.kind='pokemon' AND o.pokemon_id=?
                   AND (o.version_id IS NULL OR o.version_id=?)""",
                (species, version),
            ).fetchall()
            if rows != [(place,)]:
                errors.append(f"HGSS : repère fixe absent ou incorrect : {species}/{version} ({place})")
    return errors


def _validate_map_placement(connection: sqlite3.Connection) -> list[str]:
    from .preview_placement_hgss import exceptions

    errors = []
    if connection.execute(
        """SELECT count(*) FROM map WHERE version_group_id=10
           AND (identifier LIKE 'johto-lower%' OR identifier LIKE 'kanto-lower%')"""
    ).fetchone()[0]:
        errors.append("HGSS : coupes techniques présentes sur la carte monde")
    for header, kind in exceptions():
        count = connection.execute(
            "SELECT count(*) FROM map_spot WHERE map_id=? AND kind=?", (10_000 + header, kind)
        ).fetchone()[0]
        if count:
            errors.append(f"HGSS : terrain exclu avec marqueurs : {header}/{kind}")
    return errors


def export_recipe() -> dict[str, str]:
    names = (
        "maps_export_hgss.py",
        "safari_atlas_hgss.py",
        "plans_application_hgss.py",
        "maps_characters_hgss.py",
        "maps_offers_hgss.py",
        "builder_wild_hgss.py",
        "builder_safari_hgss.py",
        "layers_application_hgss.py",
        "origins_hgss.py",
        "references_hgss.py",
        "offers_persistent_hgss.py",
        "passages_characters_hgss.py",
        "locations_hgss.py",
        "builder_pokemon_hgss.py",
        "guide_resources_hgss.py",
        "guide_tables_hgss.py",
        "guide_scenes_hgss.py",
        "roamers_hgss.py",
        "fixed_application_hgss.py",
        "maps_fixed_hgss.py",
    )
    return {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in names
    }
