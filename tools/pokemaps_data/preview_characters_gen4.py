"""Aperçu PC des personnages DS : dresseurs, combats, revanches, objets des lieux et Pokédex National.

Il réunit, pour chaque famille de Sinnoh, ce que lisent les lecteurs de la phase 5 (pret_gen4_trainers,
pret_gen4_rematches, pret_gen4_battles, pret_gen4_field_items, pret_gen4_national_dex) dans
tools/build/preview/sinnoh-characters/characters.json. Seuls les lieux retenus pour les cartes
(maps_layout_gen4.selected_headers) sont parcourus. Rien n'entre dans les assets de l'application avant
l'activation des jeux DS (phase 6) ; les noms français des classes et des personnages ne sont pas encore joints.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .games import GEN4_GAMES, Game
from .maps_layout_gen4 import selected_headers
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_battles import (
    EventTrainer,
    FollowerPartner,
    ScriptBattle,
    read_event_trainers,
    read_follower_partners,
    read_script_battles,
)
from .pret_gen4_field_items import Gen4MapItem, hidden_coin_events, read_map_items
from .pret_gen4_flow import SET_FLAG
from .pret_gen4_national_dex import NationalDexUnlock, read_national_dex
from .pret_gen4_rematches import VsSeekerRules
from .pret_gen4_trainers import Gen4Trainer
from .sources import PRET_COMMITS, fetch_pret

PREVIEW_NAME = "sinnoh-characters"
SCHEMA = 1


@dataclass(frozen=True)
class CharacterCatalog:
    version_group: str
    repo: str
    commit: str
    headers: dict[int, str]  # numéro -> constante des lieux retenus
    trainers: tuple[Gen4Trainer, ...]
    vs_seeker: VsSeekerRules
    # Lieux dont les scripts définissent le drapeau de chaque niveau du Cherche VS (niveaux 1 à 5).
    vs_seeker_unlocks: tuple[tuple[str, ...], ...]
    event_trainers: tuple[EventTrainer, ...]
    script_battles: tuple[ScriptBattle, ...]
    follower_partners: tuple[FollowerPartner, ...]
    script_headers: dict[int, tuple[str, ...]]  # fichier de scripts -> lieux retenus qui l'emploient
    items: tuple[Gen4MapItem, ...]
    national_dex: NationalDexUnlock


def character_catalog(repo: Gen4PretRepo, game: Game) -> CharacterCatalog:
    headers = selected_headers(repo)
    users: dict[int, list[str]] = {}
    for index in sorted(headers):
        users.setdefault(headers[index].scripts, []).append(headers[index].constant)
    files = set(users)
    if coins := hidden_coin_events(repo):
        raise ValueError(f"{game.version_group} : jetons cachés à traiter : {coins}")
    catalog = CharacterCatalog(
        game.version_group,
        game.pret_repo,
        PRET_COMMITS[game.pret_repo],
        {index: header.constant for index, header in sorted(headers.items())},
        tuple(repo.trainers[number] for number in sorted(repo.trainers)),
        repo.vs_seeker,
        _flag_sites(repo, users, repo.vs_seeker.unlock_flags),
        read_event_trainers(repo, headers),
        read_script_battles(repo, files),
        read_follower_partners(repo, files),
        {index: tuple(places) for index, places in sorted(users.items())},
        read_map_items(repo, repo.script_ids, headers),
        read_national_dex(repo, headers),
    )
    validate_character_catalog(catalog)
    return catalog


def _flag_sites(repo: Gen4PretRepo, users: dict[int, list[str]], flags: tuple[int, ...]) -> tuple[tuple[str, ...], ...]:
    sites = []
    for flag in flags:
        files = {
            index
            for index in users
            if any(step.command == SET_FLAG and step.arguments[0] == flag for step in repo.flows[index].steps.values())
        }
        sites.append(tuple(sorted(place for index in files for place in users[index])))
    return tuple(sites)


def validate_character_catalog(catalog: CharacterCatalog) -> None:
    where = catalog.version_group
    known = {trainer.id for trainer in catalog.trainers}
    used = [event.trainer for event in catalog.event_trainers]
    used += [partner.trainer for partner in catalog.follower_partners]
    for battle in catalog.script_battles:
        if not battle.variants or battle.script_file not in catalog.script_headers:
            raise ValueError(f"{where} : combat sans équipe ou hors des lieux retenus : {battle.step}")
        for variant in battle.variants:
            used += [*variant.opponents, *([variant.partner] if variant.partner else [])]
    for series in catalog.vs_seeker.series:
        used += [team for team in series.teams if team is not None]
    if unknown := sorted(set(used) - known):
        raise ValueError(f"{where} : dresseurs inconnus : {unknown}")
    if any(not sites for sites in catalog.vs_seeker_unlocks):
        raise ValueError(f"{where} : niveau du Cherche VS débloqué par aucun lieu retenu")
    places = set(catalog.headers)
    if any(item.header not in places or not item.flag for item in catalog.items):
        raise ValueError(f"{where} : objet hors des lieux retenus ou sans drapeau")
    keys = [(item.header, item.kind, item.x, item.z, item.script) for item in catalog.items]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{where} : objet répété")
    events = [(event.header, event.event) for event in catalog.event_trainers]
    if len(events) != len(set(events)) or not catalog.event_trainers:
        raise ValueError(f"{where} : dresseurs posés absents ou répétés")


def unbound_trainers(catalog: CharacterCatalog) -> tuple[int, ...]:
    """Dresseurs qu'aucun PNJ, combat de script, partenaire ou revanche des lieux retenus n'emploie."""
    bound = {event.trainer for event in catalog.event_trainers} | {p.trainer for p in catalog.follower_partners}
    for battle in catalog.script_battles:
        for variant in battle.variants:
            bound |= {*variant.opponents, *([variant.partner] if variant.partner else [])}
    series = {series.base: series for series in catalog.vs_seeker.series}
    bound |= {team for base in list(bound) if base in series for team in series[base].teams if team is not None}
    return tuple(sorted({trainer.id for trainer in catalog.trainers} - bound))


def build_characters_preview_gen4(cache: Path, preview: Path) -> None:
    started = time.monotonic()
    target = preview / PREVIEW_NAME
    catalogs = []
    for game in GEN4_GAMES:
        repo = Gen4PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        catalogs.append(character_catalog(repo, game))
    target.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA, "families": [asdict(catalog) for catalog in catalogs]}
    (target / "characters.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for catalog in catalogs:
        print(
            f"{catalog.version_group} : {len(catalog.trainers)} dresseurs, {len(catalog.event_trainers)} posés, "
            f"{len(catalog.script_battles)} combats de script, {len(catalog.items)} objets, "
            f"{len(unbound_trainers(catalog))} dresseurs sans lieu retenu"
        )
    print(f"Aperçu des personnages DS validé : {target} ({time.monotonic() - started:.1f} s)")
