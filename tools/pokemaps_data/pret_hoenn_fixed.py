"""Rencontres fixes de Hoenn, lues dans les événements interactifs pret."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .games import GEN3_GAMES
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_conditions import ScriptRequirement, script_states
from .pret_gen3_script_values import number_value
from .sources import PRET_COMMITS, fetch_pret

_MAPS = frozenset(
    {
        "AncientTomb",
        "DesertRuins",
        "IslandCave",
        "CaveOfOrigin_B4F",
        "TerraCave_End",
        "MarineCave_End",
        "SkyPillar_Top",
        "AquaHideout_B1F",
        "TeamAquaHideout_B1F",
        "TeamMagmaHideout_B1F",
        "Route119",
        "Route120",
        "SouthernIsland_Interior",
    }
)


def fixed_encounters(repo: Gen3PretRepo, version: str) -> list[dict[str, object]]:
    reader = repo.offers[version]
    rows: list[dict[str, object]] = []
    for current in sorted(repo.maps.values(), key=lambda current: current.number):
        if current.label not in _MAPS:
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
                position = event
                if "var" in fields or current.label == "SouthernIsland_Interior":
                    candidates = [
                        obj for obj in current.objects if str(dict(obj.fields).get("script")) in {"0", "0x0", "NULL"}
                    ]
                    expected = 2 if current.label == "SouthernIsland_Interior" else 1
                    if len(candidates) != expected:
                        raise ValueError(f"{current.label} : position du Pokémon fixe ambiguë")
                    # Sur l'Île du Sud, le premier objet est la pierre, le second le Pokémon.
                    position = candidates[-1]
                level = number_value(args[1], reader.scripts.constants)
                if args[0] not in reader.scripts.constants or level is None or not 1 <= level <= 100:
                    raise ValueError(f"{instruction.source} : Pokémon fixe invalide : {args}")
                removal_flag = str(dict(position.fields).get("flag", flag))
                paths = state.requirements
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
                    "event": current.label == "SouthernIsland_Interior",
                    "requirements": [asdict(requirement) for requirement in sorted(paths)],
                }
                if row not in rows:
                    rows.append(row)
    return rows


def build_fixed_catalog(cache: Path, assets: Path) -> None:
    for game in GEN3_GAMES:
        if game.pret_repo == "pokefirered":
            continue
        repo = Gen3PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        versions = {version: fixed_encounters(repo, version) for version, _ in game.pret_versions}
        for version, rows in versions.items():
            required = {"REGIROCK", "REGICE", "REGISTEEL", "RAYQUAZA", "ELECTRODE", "KECLEON"}
            required |= (
                {"GROUDON", "KYOGRE", "LATIOS", "LATIAS"}
                if version == "emerald"
                else ({"GROUDON", "LATIAS"} if version == "ruby" else {"KYOGRE", "LATIOS"})
            )
            missing = {"SPECIES_" + name for name in required} - {row["pokemon"] for row in rows}
            if missing:
                raise ValueError(f"{version} : Pokémon fixes absents : {sorted(missing)}")
        target = assets / "maps" / game.version_group / "fixed_encounters.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        content = {"schema": 1, "repo": game.pret_repo, "commit": PRET_COMMITS[game.pret_repo], "versions": versions}
        target.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
