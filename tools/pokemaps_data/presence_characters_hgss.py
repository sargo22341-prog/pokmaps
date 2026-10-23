"""Conditions de présence : chemins natifs qui lèvent le drapeau de masquage."""

from dataclasses import asdict

from .conditions_hgss import translate_conditions
from .pret_gen4_flow_chains import Chains
from .pret_hgss_flow import HgssFlow


def attach_presence(actors: list[dict], flows: dict[int, HgssFlow], constants: dict[str, int]) -> None:
    requested = {
        (a["bank"], constants[a["native"]["flag"]])
        for a in actors
        if a["useful"] and a["native"]["flag"] != "FLAG_NOTHING"
    }
    resolved = {}
    registration = {
        (a["bank"], constants[a["native"]["flag"]])
        for a in actors
        if a["native"]["sprite"].startswith("SPRITE_GSLEADER")
        and any(s.command == "RegisterGearNumber" for s in flows[a["bank"]].flow.steps.values())
    }
    for bank in sorted({bank for bank, _ in requested}):
        adapted = flows[bank]
        chains = Chains(adapted.flow)
        for step in adapted.flow.steps.values():
            if step.command != "ClearFlag" or (bank, step.arguments[0]) not in requested:
                continue
            exhaustive = (bank, step.arguments[0]) in registration
            conditions = chains.paths(step.key) if exhaustive else (chains.conditions(step.key),)
            paths = [[asdict(condition) for condition in path] for path in conditions]
            resolved.setdefault((bank, step.arguments[0]), []).append(
                dict(
                    source=adapted.flow.name,
                    instruction=adapted.original[int(step.key)],
                    paths=paths,
                    paths_fr=[translate_conditions(path) for path in paths],
                    exhaustive=exhaustive,
                )
            )
    for actor in actors:
        actor["presence"] = dict(
            hidden_when_flag_set=actor["native"]["flag"],
            reveal_paths=resolved.get((actor["bank"], constants[actor["native"]["flag"]]), []),
        )
