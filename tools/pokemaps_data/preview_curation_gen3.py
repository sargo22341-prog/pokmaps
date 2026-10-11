"""Rapport reproductible des personnages GBA corrigés, dans l'aperçu local."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .character_curation_gen3 import Gen3Curation, OfferResolution, character_key, read_gen3_curation
from .games import GEN3_GAMES, Game
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_offers import ScriptOffers
from .pret_hoenn_fixed import fixed_encounters
from .sources import PRET_COMMITS, fetch_pret


def build_curation_preview(cache: Path, output: Path) -> None:
    curation = read_gen3_curation()
    duplicates: set[tuple[str, str]] = set()
    resolutions: set[OfferResolution] = set()
    versions: list[dict[str, object]] = []
    for game in GEN3_GAMES:
        repo = Gen3PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        versions.extend(_game_rows(game, repo, curation, duplicates, resolutions))
    if duplicates != set(curation.duplicates) or resolutions != set(curation.resolutions):
        missing = (set(curation.duplicates) - duplicates, set(curation.resolutions) - resolutions)
        raise ValueError(f"Curation GBA : lignes sans personnage : {missing}")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "character_curation.json"
    target.write_text(
        json.dumps({"schema": 1, "versions": versions}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Curation GBA : {len(versions)} versions validées ; {target}")


def _game_rows(
    game: Game,
    repo: Gen3PretRepo,
    curation: Gen3Curation,
    duplicates: set[tuple[str, str]],
    resolutions: set[OfferResolution],
) -> list[dict[str, object]]:
    versions: list[dict[str, object]] = []
    for version, _ in game.pret_versions:
        characters: list[dict[str, object]] = []
        for current in sorted(repo.maps.values(), key=lambda current: current.number):
            for index, event in enumerate(current.objects, 1):
                key = character_key(current.label, event, index)
                duplicate = curation.is_duplicate(game.map_family, key)
                if event.kind == "clone":
                    continue
                rows = curation.rows_for(game.pret_repo, key, str(event.value("script")))
                result = repo.offers[version].read_curated_object(current.label, event, index, game.map_family)
                if result.unresolved:
                    raise ValueError(f"{version}:{key} : résolution éditoriale incomplète : {result.unresolved}")
                if duplicate:
                    duplicates.add((game.map_family, key))
                resolutions.update(rows)
                characters.append(
                    {
                        "key": key,
                        "excluded": duplicate,
                        "script": event.value("script"),
                        "event": dict(event.fields),
                        "x": event.x,
                        "y": event.y,
                        "elevation": event.elevation,
                        "removal_flag": event.value("flag"),
                        "exclusion_reason": curation.duplicate_reason(game.map_family, key),
                        "dynamic_position": current.label.startswith(
                            ("BattlePyramidSquare", "BattleFrontier_BattlePyramid")
                        ),
                        "result": _result_row(result),
                        "reasons": sorted({row.reason for row in rows}),
                    }
                )
        versions.append(
            {
                "version": version,
                "repo": game.pret_repo,
                "commit": PRET_COMMITS[game.pret_repo],
                "characters": characters,
                "fixed_encounters": fixed_encounters(repo, version) if not repo.remake else [],
            }
        )
    return versions


def _result_row(result: ScriptOffers) -> dict[str, object]:
    offers: list[dict[str, object]] = []
    for offer in result.offers:
        row = asdict(offer)
        row["paths"] = [[asdict(requirement) for requirement in sorted(path)] for path in offer.paths]
        offers.append(row)
    return {"offers": offers, "trainers": result.trainers, "flags": result.flags, "specials": result.specials}
