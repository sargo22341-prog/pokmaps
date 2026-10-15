"""Rencontres fixes GBA, lues dans les événements interactifs pret."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .games import GEN3_GAMES
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_conditions import ScriptRequirement, script_states
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_script_values import number_value
from .sources import PRET_COMMITS, fetch_pret
from .validate_remake_fixed import validate_remake_rows

_HOENN_MAPS = frozenset(
    {
        "AncientTomb",
        "DesertRuins",
        "IslandCave",
        "CaveOfOrigin_B4F",
        "TerraCave_End",
        "MarineCave_End",
        "SkyPillar_Top",
        "AquaHideout_B1F",
        "MagmaHideout_B1F",
        "NewMauville_Inside",
        "Route119",
        "Route120",
        "SouthernIsland_Interior",
    }
)


_REMAKE_MAPS = frozenset(
    {
        "Route12",
        "Route16",
        "PowerPlant",
        "ThreeIsland_BerryForest",
        "SeafoamIslands_B4F",
        "MtEmber_Summit",
        "CeruleanCave_B1F",
        "NavelRock_Summit",
        "NavelRock_Base",
        "BirthIsland_Exterior",
    }
)
_EVENT_MAPS = frozenset({"SouthernIsland_Interior", "NavelRock_Summit", "NavelRock_Base", "BirthIsland_Exterior"})


def _pokemon_position(current: Gen3Map, event: Gen3Event) -> Gen3Event:
    if current.label == "Route120" and event.value("graphics_id") == "OBJ_EVENT_GFX_STEVEN":
        candidates = [
            obj for obj in current.objects if "KECLEON" in str(obj.value("graphics_id")) and obj.elevation == 4
        ]
        if len(candidates) != 1:
            raise ValueError("Route120 : Kecleon du pont absent ou ambigu")
        return candidates[0]
    remote = {"SouthernIsland_Interior", "BirthIsland_Exterior"}
    if "var" not in dict(event.fields) and current.label not in remote:
        return event
    candidates = [obj for obj in current.objects if str(dict(obj.fields).get("script")) in {"0", "0x0", "NULL"}]
    expected = 2 if current.label == "SouthernIsland_Interior" else 1
    if len(candidates) != expected:
        raise ValueError(f"{current.label} : position du Pokémon fixe ambiguë")
    # Sur l'Île du Sud, le premier objet est la pierre, le second le Pokémon.
    return candidates[-1]


def _access_requirements(label: str) -> frozenset[ScriptRequirement]:
    # Le marin de Carmin sur Mer vérifie ces drapeaux avant les tickets (VermilionCity/scripts.inc).
    access = {
        "NavelRock_Summit": "FLAG_ENABLE_SHIP_NAVEL_ROCK",
        "NavelRock_Base": "FLAG_ENABLE_SHIP_NAVEL_ROCK",
        "BirthIsland_Exterior": "FLAG_ENABLE_SHIP_BIRTH_ISLAND",
    }
    flag = access.get(label)
    return frozenset({ScriptRequirement(flag, "eq", "TRUE")}) if flag else frozenset()


def fixed_encounters(repo: Gen3PretRepo, version: str) -> list[dict[str, object]]:
    reader = repo.offers[version]
    rows: list[dict[str, object]] = []
    for current in sorted(repo.maps.values(), key=lambda current: current.number):
        if not _active_fixed_map(repo, current.label, version):
            continue
        for event in (*current.objects, *current.bg_events, *current.coord_events):
            fields = dict(event.fields)
            label = str(fields.get("script", "0"))
            if label in {"0", "0x0", "NULL"} or event.kind == "clone":
                continue
            flag = str(fields.get("flag", "0"))
            requirements = (
                frozenset({ScriptRequirement(flag, "eq", "FALSE")}) if flag.startswith("FLAG_") else frozenset()
            )
            if "var" in fields:
                requirements |= frozenset({ScriptRequirement(str(fields["var"]), "eq", str(fields["var_value"]))})
            for state in script_states(reader.scripts, label, requirements):
                instruction = reader.scripts.instruction(state.point)
                if instruction is None or instruction.command not in {"setwildbattle", "seteventmon"}:
                    continue
                args = tuple(state.value(value) for value in instruction.args)
                position = _pokemon_position(current, event)
                level = number_value(args[1], reader.scripts.constants)
                if args[0] not in reader.scripts.constants or level is None or not 1 <= level <= 100:
                    raise ValueError(f"{instruction.source} : Pokémon fixe invalide : {args}")
                removal_flag = str(dict(position.fields).get("flag", flag))
                paths = state.requirements | _access_requirements(current.label)
                if removal_flag.startswith("FLAG_"):
                    paths |= frozenset({ScriptRequirement(removal_flag, "eq", "FALSE")})
                row = {
                    "map": current.label,
                    "x": position.x,
                    "y": position.y,
                    "elevation": position.elevation,
                    "script": label,
                    "source": instruction.source,
                    "pokemon": args[0],
                    "level": level,
                    "held_item": args[2] if len(args) > 2 and args[2] not in {"0", "ITEM_NONE"} else None,
                    "removal_flag": removal_flag,
                    "event": current.label in _EVENT_MAPS,
                    "requirements": [asdict(requirement) for requirement in sorted(paths)],
                }
                if repo.remake:
                    row["access_item"] = _access_item(current.label)
                if row not in rows:
                    rows.append(row)
    return rows


def _active_fixed_map(repo: Gen3PretRepo, label: str, version: str) -> bool:
    if label not in (_REMAKE_MAPS if repo.remake else _HOENN_MAPS):
        return False
    # Nénucrique ouvre seulement la planque de la team propre à la cartouche.
    if repo.ruby and label in {"AquaHideout_B1F", "MagmaHideout_B1F"}:
        return label == ("MagmaHideout_B1F" if version == "ruby" else "AquaHideout_B1F")
    return True


def build_fixed_catalog(cache: Path, assets: Path, group: str | None = None) -> None:
    for game in GEN3_GAMES:
        if group == "hoenn" and game.pret_repo == "pokefirered":
            continue
        if group not in {None, "hoenn"} and game.version_group != group:
            continue
        repo = Gen3PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        versions = {version: fixed_encounters(repo, version) for version, _ in game.pret_versions}
        for version, rows in versions.items():
            if repo.remake:
                validate_remake_rows(version, rows)
            required = {"REGIROCK", "REGICE", "REGISTEEL", "RAYQUAZA", "ELECTRODE", "KECLEON"}
            required |= (
                {"GROUDON", "KYOGRE", "LATIOS", "LATIAS"}
                if version == "emerald"
                else ({"GROUDON", "LATIAS"} if version == "ruby" else {"KYOGRE", "LATIOS"})
            )
            if repo.remake:
                required = {
                    "SNORLAX",
                    "ELECTRODE",
                    "ARTICUNO",
                    "ZAPDOS",
                    "MOLTRES",
                    "MEWTWO",
                    "HO_OH",
                    "LUGIA",
                    "DEOXYS",
                }
            missing = {"SPECIES_" + name for name in required} - {row["pokemon"] for row in rows}
            if missing:
                raise ValueError(f"{version} : Pokémon fixes absents : {sorted(missing)}")
        target = assets / "maps" / game.version_group / "fixed_encounters.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        content = {"schema": 1, "repo": game.pret_repo, "commit": PRET_COMMITS[game.pret_repo], "versions": versions}
        target.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _access_item(label: str) -> str | None:
    if label in {"NavelRock_Summit", "NavelRock_Base"}:
        return "ITEM_MYSTIC_TICKET"
    if label == "BirthIsland_Exterior":
        return "ITEM_AURORA_TICKET"
    return None
