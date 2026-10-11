"""Conditions des scènes automatiques conservées avec les personnages GBA."""

from __future__ import annotations

from .maps_offers_gen3 import repo_name
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_conditions import ScriptRequirement
from .story_events import StoryEvents


def scene_rows(repo: Gen3PretRepo, story: StoryEvents) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    name = repo_name(repo)
    for version, _ in repo.versions:
        scripts = repo.offers[version].scripts
        for label, block in sorted(scripts.blocks.items()):
            for line in block.lines:
                if line.command != "map_script_2":
                    continue
                subject, value, target = line.args
                number = scripts.constants.get(value, value)
                requirement = ScriptRequirement(subject, "eq", str(number))
                phrases = (
                    story.script_phrases(name, frozenset({requirement}), line.source)
                    if (name, requirement) in story.values
                    else ()
                )
                rows.append(
                    {
                        "version": version,
                        "table": label,
                        "variable": subject,
                        "value": str(number),
                        "script": target,
                        "conditions": phrases,
                    }
                )
    return rows
