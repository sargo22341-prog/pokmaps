"""Cartes GBA préparatoires, avant l'intégration des rencontres et personnages."""

from __future__ import annotations

import csv
import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path

from .games import EMERALD, EXTERNAL_EVENT_NOTE, FIRERED_LEAFGREEN, RUBY_SAPPHIRE, Game
from .maps import MapRow, WarpRow, display_map_rows, read_map_names
from .maps_layout import identifier, read_layout_curation
from .maps_layout_gen3 import Gen3GameMaps
from .maps_render_gen3 import Gen3Renderer
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_source import read_json
from .sources import fetch_pret

HOENN_MAP_GAMES = (EMERALD, RUBY_SAPPHIRE)
GEN3_MAP_GAMES = (*HOENN_MAP_GAMES, FIRERED_LEAFGREEN)


def _static_sprite(obj: Gen3Event) -> str | None:
    # Les journaux du Memorydex sont des objets interactifs invisibles, pas des personnages.
    if obj.value("movement_type") == "MOVEMENT_TYPE_INVISIBLE":
        return None
    sprite = str(obj.value("graphics_id"))
    return None if sprite.startswith("OBJ_EVENT_GFX_VAR_") else sprite


def _warps(game_maps: Gen3GameMaps) -> list[WarpRow]:
    result = []
    for const, current in game_maps.maps.items():
        for warp in current.warps:
            # Le bateau et le Dôme placent aussi des warps hors layout pour leurs déplacements scriptés.
            if not warp.accessible or not (0 <= warp.x < current.width and 0 <= warp.y < current.height):
                continue
            target, point = None, (None, None)
            if warp.target in game_maps.maps:
                target = warp.target
                if 0 < warp.target_warp < 127:
                    destination = game_maps.maps[target]
                    if warp.target_warp > len(destination.warps):
                        raise ValueError(f"{const} : warp d’arrivée absent : {target} #{warp.target_warp}")
                    arrival = destination.warps[warp.target_warp - 1]
                    if 0 <= arrival.x < destination.width and 0 <= arrival.y < destination.height:
                        point = game_maps.point(target, arrival.x, arrival.y)
            result.append(WarpRow(const, *game_maps.point(const, warp.x, warp.y), target, *point))
    return result


def _write_catalog(rows: list[MapRow], warps: list[WarpRow], output: Path) -> None:
    fields = tuple(asdict(rows[0]))
    with (output / "catalog.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    with (output / "warps.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, tuple(asdict(warps[0])), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in warps)


def _write_events(game_maps: Gen3GameMaps, output: Path) -> None:
    events = {
        const: {
            "objects": [asdict(obj) for obj in current.objects],
            "coord_events": [asdict(event) for event in current.coord_events],
            "bg_events": [asdict(event) for event in current.bg_events],
            "warps": [asdict(warp) for warp in current.warps],
            "connections": [asdict(connection) for connection in current.connections],
            "map_type": current.map_type,
            "region_map_section": current.region_map_section,
            "layout": current.layout.const,
            "notes": _map_notes(current),
        }
        for const, current in game_maps.maps.items()
    }
    path = output / "events.json"
    path.write_text(json.dumps(events, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _map_notes(current: Gen3Map) -> tuple[str, ...]:
    notes = []
    if current.const.startswith(("MAP_FARAWAY_ISLAND", "MAP_BIRTH_ISLAND", "MAP_NAVEL_ROCK", "MAP_SOUTHERN_ISLAND")):
        notes.append(EXTERNAL_EVENT_NOTE)
    if current.map_type == "MAP_TYPE_SECRET_BASE":
        notes.append("Modèle de Base Secrète ; entrée et décorations variables.")
    if (
        current.const.startswith("MAP_BATTLE_PYRAMID_SQUARE")
        or current.const == "MAP_BATTLE_FRONTIER_BATTLE_PYRAMID_FLOOR"
    ):
        notes.append("Modèle de la Pyramide de Combat ; assemblage aléatoire non simulé.")
    if current.const.startswith("MAP_BATTLE_FRONTIER_BATTLE_PIKE_ROOM_"):
        notes.append("Modèle du Reptile de Combat ; tirage aléatoire non simulé.")
    if any(str(obj.value("graphics_id")).startswith("OBJ_EVENT_GFX_VAR_") for obj in current.objects):
        notes.append("L’apparence de certains personnages dépend du scénario.")
    return tuple(notes)


def export_gen3_maps(cache: Path, output: Path, game: Game) -> tuple[int, int, int]:
    repo = Gen3PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
    game_maps = Gen3GameMaps(repo, game, read_layout_curation())
    names = read_map_names()[game.map_family] | {const: plan.name for const, plan in game_maps.plans.items()}
    if missing := sorted((set(game_maps.placements) | set(game_maps.world_blocks)) - names.keys()):
        raise ValueError(f"maps.csv : noms français GBA manquants : {missing}")
    if output.name != game.version_group or output.is_symlink():
        raise ValueError(f"Dossier de cartes GBA invalide : {output}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    renderer = Gen3Renderer(game_maps, repo)
    rows = display_map_rows(game_maps, names, renderer, output)
    warps = _warps(game_maps)
    sprites = {
        sprite
        for current in game_maps.maps.values()
        for obj in current.objects
        if (sprite := _static_sprite(obj)) is not None
    }
    renderer.write_sprites(sprites, output / "sprites")
    _write_catalog(rows, warps, output)
    _write_events(game_maps, output)
    validate_catalog(output)
    tiles = [path for path in output.rglob("*.webp") if path.parent.name.isdecimal()]
    return len(rows), len(tiles), sum(path.stat().st_size for path in output.rglob("*") if path.is_file())


def build_gen3_maps(cache: Path, output: Path, games: tuple[Game, ...] = GEN3_MAP_GAMES) -> None:
    started = time.monotonic()
    for game in games:
        maps, tiles, size = export_gen3_maps(cache, output / game.version_group, game)
        print(f"  {game.version_group} : {maps} cartes/zones, {tiles} tuiles, {size / 1024 / 1024:.2f} Mio")
    print(f"Cartes GBA générées en {time.monotonic() - started:.1f} s")


def validate_catalog(output: Path) -> None:
    with (output / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not 0 < len(rows) <= 1024:
        raise ValueError(f"{output} : catalogue de cartes vide ou trop grand")
    maps = {row["const"]: row for row in rows}
    if len(maps) != len(rows) or len({row["number"] for row in rows}) != len(rows):
        raise ValueError(f"{output} : cartes ou numéros répétés")
    for row in rows:
        _validate_row(output, row, maps)
    with (output / "warps.tsv").open(encoding="utf-8", newline="") as handle:
        for warp in csv.DictReader(handle, delimiter="\t"):
            _validate_warp(output, warp, maps)
    _validate_events(output, maps)


def _validate_events(output: Path, maps: dict[str, dict[str, str]]) -> None:
    events = read_json(output / "events.json")
    if set(events) != {const for const in maps if const.startswith("MAP_")}:
        raise ValueError(f"{output} : événements absents ou étrangers au catalogue")
    for const, current in events.items():
        for obj in current["objects"]:
            fields = dict(obj["fields"])
            if fields["movement_type"] == "MOVEMENT_TYPE_INVISIBLE":
                continue
            sprite = str(fields["graphics_id"])
            if sprite.startswith("OBJ_EVENT_GFX_VAR_"):
                if "L’apparence de certains personnages dépend du scénario." not in current["notes"]:
                    raise ValueError(f"{output} : apparence variable non signalée : {const}")
                continue
            path = output / "sprites" / f"{sprite.lower().replace('_', '-')}.webp"
            if not path.is_file():
                raise ValueError(f"{output} : sprite absent : {const} : {path.name}")


def _validate_row(output: Path, row: dict[str, str], maps: dict[str, dict[str, str]]) -> None:
    const = row["const"]
    if not row["name_fr"].strip() or int(row["width"]) <= 0 or int(row["height"]) <= 0:
        raise ValueError(f"{output} : nom ou dimensions invalides : {const}")
    parent = row["parent"]
    if parent:
        if parent not in maps or maps[parent]["parent"] or int(row["level_count"]) != 0:
            raise ValueError(f"{output} : parent invalide : {const}")
        container = maps[parent]
        if any(
            int(row[axis]) < 0 or int(row[axis]) + int(row[size]) > int(container[size])
            for axis, size in (("x", "width"), ("y", "height"))
        ):
            raise ValueError(f"{output} : zone hors de sa carte : {const}")
    else:
        for level in range(int(row["level_count"])):
            if not any((output / identifier(const) / str(level)).glob("*.webp")):
                raise ValueError(f"{output} : tuiles absentes : {const} niveau {level}")
    for field in ("origin", "start"):
        if row[field] and row[field] not in maps:
            raise ValueError(f"{output} : référence {field} absente : {const}")


def _validate_warp(output: Path, warp: dict[str, str], maps: dict[str, dict[str, str]]) -> None:
    for const_field, x_field, y_field in (("map_const", "x", "y"), ("target", "target_x", "target_y")):
        const = warp[const_field]
        if not const:
            if warp[x_field] or warp[y_field]:
                raise ValueError(f"{output} : warp sans destination avec coordonnées")
            continue
        if const not in maps:
            raise ValueError(f"{output} : destination de warp absente : {const}")
        if bool(warp[x_field]) != bool(warp[y_field]):
            raise ValueError(f"{output} : coordonnées de warp incomplètes : {const}")
        if not warp[x_field]:
            continue  # Warps de Base Secrète ou de retour : la destination dépend du joueur.
        row = maps[const]
        x, y = int(warp[x_field]), int(warp[y_field])
        if not (
            int(row["x"]) <= x < int(row["x"]) + int(row["width"])
            and int(row["y"]) <= y < int(row["y"]) + int(row["height"])
        ):
            raise ValueError(f"{output} : warp hors de la zone {const} : {x}, {y}")
