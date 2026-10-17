"""Corrections éditoriales GBA, sans perdre la provenance ni les conditions des scripts."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_gen3_conditions import ScriptRequirement
from .pret_gen3_maps import Gen3Event
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .pret_gen3_offers import Gen3Offer, ScriptOffers

GEN3_REPOS = frozenset({"pokeruby", "pokeemerald", "pokefirered"})


def character_key(map_label: str, event: Gen3Event, index: int) -> str:
    """L'identifiant local appartient à une carte ; le script seul peut être partagé."""
    return f"{map_label}:{dict(event.fields).get('local_id', index)}"


@dataclass(frozen=True)
class OfferResolution:
    repos: frozenset[str]
    key: str
    expression: str
    item: str | None
    reason: str
    kind: str = "gift_item"
    move: str | None = None
    quantity: str | None = None
    source: str = ""
    conditions: tuple[str, ...] = ()
    price: int | None = None
    pokemon: str | None = None
    required_flag: str | None = None

    def matches(self, offer: Gen3Offer) -> bool:
        kind = "move_tutor" if self.kind == "move_tutor" else "gift_item"
        value = offer.move if kind == "move_tutor" else offer.item
        return offer.kind == kind and value == self.expression and (not self.source or self.source == offer.source)


@dataclass(frozen=True)
class Gen3Curation:
    duplicates: tuple[tuple[str, str], ...]
    resolutions: tuple[OfferResolution, ...]
    duplicate_reasons: tuple[tuple[str, str, str], ...] = ()

    def is_duplicate(self, family: str, key: str) -> bool:
        return (family, key) in self.duplicates

    def duplicate_reason(self, family: str, key: str) -> str:
        return next((reason for group, actor, reason in self.duplicate_reasons if (group, actor) == (family, key)), "")

    def rows_for(self, repo: str, key: str, script: str = "") -> tuple[OfferResolution, ...]:
        return tuple(row for row in self.resolutions if repo in row.repos and row.key in {key, f"@script:{script}"})

    def apply(self, repo: str, key: str, result: ScriptOffers, script: str = "") -> ScriptOffers:
        rows = self.rows_for(repo, key, script)
        for row in rows:
            if not any(row.matches(offer) for offer in result.offers):
                raise ValueError(f"npc_offers.csv : résolution inutilisée : {repo}:{key}:{row.expression}")
        offers: list[Gen3Offer] = []
        for offer in result.offers:
            matching = tuple(row for row in rows if row.matches(offer))
            if matching:
                offers.extend(_resolved_offer(offer, row) for row in matching)
            else:
                offers.append(offer)
        # La résolution d'un objet n'atteste pas les autres effets des appels C.
        return replace(result, offers=tuple(offers))


def _resolved_offer(offer: Gen3Offer, row: OfferResolution) -> Gen3Offer:
    if row.quantity and offer.quantity and offer.quantity.isdecimal() and row.quantity != offer.quantity:
        raise ValueError(f"npc_offers.csv : quantité du script modifiée : {row.key}:{offer.source}")
    paths = offer.paths
    if row.required_flag:
        requirement = ScriptRequirement(row.required_flag, "eq", "FALSE")
        if any(_requires_set(path, row.required_flag) for path in paths):
            raise ValueError(f"npc_offers.csv : drapeau incompatible avec le script : {row.key}:{row.required_flag}")
        paths = tuple(path | {requirement} for path in paths)
    return replace(
        offer,
        kind=row.kind,
        item=row.item,
        move=row.move,
        quantity=row.quantity or offer.quantity,
        conditions=row.conditions,
        price=row.price,
        currency="battle_points" if row.price else None,
        eligible_pokemon=row.pokemon,
        paths=paths,
    )


def _requires_set(path: frozenset[ScriptRequirement], flag: str) -> bool:
    return any(
        requirement.subject == flag
        and (
            (requirement.operator == "eq" and requirement.value in {"TRUE", "1"})
            or (requirement.operator == "ne" and requirement.value in {"FALSE", "0"})
        )
        for requirement in path
    )


def read_gen3_curation() -> Gen3Curation:
    with (DATA_DIR / "npc_duplicates.csv").open(encoding="utf-8", newline="") as handle:
        duplicate_rows = tuple(
            row for row in csv.DictReader(handle) if row["family"] in {"ruby-sapphire-emerald", "firered-leafgreen"}
        )
    duplicates = tuple(_duplicate(row) for row in duplicate_rows)
    if len(set(duplicates)) != len(duplicates):
        raise ValueError("npc_duplicates.csv : personnage GBA répété")
    with (DATA_DIR / "npc_offers.csv").open(encoding="utf-8", newline="") as handle:
        rows = tuple(
            row
            for row in csv.DictReader(handle)
            if row["action"] == "resolve" and not set(row["repos"].split("|")) <= {"pokeplatinum", "pokediamond"}
        )
    resolutions = tuple(_resolution(row) for row in rows)
    _check_resolution_duplicates(resolutions)
    reasons = tuple((row["family"], row["text"], row["reason"]) for row in duplicate_rows)
    return Gen3Curation(duplicates, resolutions, reasons)


def _check_resolution_duplicates(rows: tuple[OfferResolution, ...]) -> None:
    seen: set[tuple[str, str, str, str, str, str | None, str | None]] = set()
    for row in rows:
        for repo in row.repos:
            key = (repo, row.key, row.expression, row.source, row.kind, row.item, row.move)
            if key in seen:
                raise ValueError(f"npc_offers.csv : résolution GBA répétée : {key}")
            seen.add(key)


def _duplicate(row: dict[str, str]) -> tuple[str, str]:
    if ":" not in row["text"] or not row["reason"].strip():
        raise ValueError(f"npc_duplicates.csv : clé locale ou raison manquante : {row}")
    return row["family"], row["text"]


def _resolution(row: dict[str, str]) -> OfferResolution:
    repos = frozenset(row["repos"].split("|"))
    if not repos or not repos <= GEN3_REPOS or ":" not in row["text"]:
        raise ValueError(f"npc_offers.csv : dépôt ou personnage GBA invalide : {row}")
    kind = row["kind"]
    if kind not in {"gift_item", "gift_custom_item", "move_tutor"}:
        raise ValueError(f"npc_offers.csv : objet résolu invalide : {row}")
    if kind == "gift_item" and not row["item"].startswith("ITEM_"):
        raise ValueError(f"npc_offers.csv : objet résolu invalide : {row}")
    if kind != "gift_item" and row["item"]:
        raise ValueError(f"npc_offers.csv : objet inattendu : {row}")
    if kind == "move_tutor" and not row.get("move", "").startswith("MOVE_"):
        raise ValueError(f"npc_offers.csv : attaque invalide : {row}")
    if not row.get("expression", "").startswith("VAR_") or not row.get("reason", "").strip():
        raise ValueError(f"npc_offers.csv : expression ou source de relecture manquante : {row}")
    quantity, price = row.get("quantity", ""), row.get("price", "")
    if quantity not in {"", "1"} or (price and (not price.isdecimal() or not 0 < int(price) <= 100)):
        raise ValueError(f"npc_offers.csv : quantité ou prix invalide : {row}")
    if row["wanted_item"] or (row["pokemon"] and not row["pokemon"].startswith("SPECIES_")):
        raise ValueError(f"npc_offers.csv : espèce invalide : {row}")
    flag = row.get("required_flag", "")
    if flag and not flag.startswith("FLAG_"):
        raise ValueError(f"npc_offers.csv : drapeau invalide : {row}")
    _check_resolution_metadata(row)
    return OfferResolution(
        repos,
        row["text"],
        row["expression"],
        row["item"] or None,
        row["reason"],
        kind,
        row.get("move") or None,
        quantity or None,
        row.get("source", ""),
        tuple(filter(None, row.get("conditions", "").split("|"))),
        int(price) if price else None,
        row["pokemon"] or None,
        flag or None,
    )


def _check_resolution_metadata(row: dict[str, str]) -> None:
    if row.get("source") and not re.fullmatch(r"[^:\r\n]+:[1-9]\d*", row["source"]):
        raise ValueError(f"npc_offers.csv : provenance invalide : {row}")
    if row["kind"] == "gift_custom_item" and not row.get("conditions", "").strip():
        raise ValueError(f"npc_offers.csv : lot personnalisé sans condition : {row}")
    if row["kind"] != "move_tutor" and any(row.get(key) for key in ("move", "price", "pokemon", "required_flag")):
        raise ValueError(f"npc_offers.csv : métadonnées de tuteur sur un don : {row}")
