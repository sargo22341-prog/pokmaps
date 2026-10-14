"""Apparences des équipes lues dans les scripts d'initialisation de chaque version."""

from dataclasses import replace

from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_scripts import Gen3Scripts


def team_graphics(current: Gen3Map, scripts: Gen3Scripts) -> dict[str, str]:
    root = f"{current.shared_scripts_map or current.label}_MapScripts"
    if root not in scripts.blocks:
        return {}
    pending = [root]
    # Le repaire Magma conserve les variables initialisées à Nénucrique, sans les réaffecter à chaque étage.
    if current.label.startswith("MagmaHideout_"):
        pending.append("LilycoveCity_MapScripts")
    seen: set[str] = set()
    result: dict[str, str] = {}
    for _ in range(4096):
        if not pending:
            return result
        label = pending.pop()
        if label in seen:
            continue
        seen.add(label)
        for instruction in scripts.blocks[label].lines:
            args = instruction.args
            if instruction.command == "setvar" and len(args) == 2:
                variable, sprite = args
                if variable.startswith("VAR_OBJ_GFX_ID_") and any(
                    team in sprite for team in ("AQUA", "MAGMA", "ARCHIE", "MAXIE")
                ):
                    key = variable.replace("VAR_OBJ_GFX_ID_", "OBJ_EVENT_GFX_VAR_")
                    if key in result and result[key] != sprite:
                        raise ValueError(f"{current.label} : apparence d'équipe ambiguë pour {key}")
                    result[key] = sprite
            if instruction.command.startswith(("call", "goto", "map_script")):
                pending.extend(argument for argument in args if argument in scripts.blocks)
    raise ValueError(f"{current.label} : initialisation des équipes trop longue")


def apply_team_graphics(event: Gen3Event, graphics: dict[str, str]) -> Gen3Event:
    fields = dict(event.fields)
    fields["graphics_id"] = graphics.get(str(fields["graphics_id"]), fields["graphics_id"])
    return replace(event, fields=tuple(fields.items()))
