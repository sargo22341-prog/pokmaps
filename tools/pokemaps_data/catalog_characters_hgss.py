"""Assemblage des acteurs, combats, offres et rendez-vous propres à HGSS."""

from pathlib import Path

from .calendar_hgss import calendar_catalog
from .character_actors_hgss import actor_catalog
from .character_battles_hgss import bind_battles
from .character_curation_hgss import curate_actors
from .conditions_hgss import translate_conditions
from .names_hgss import native_names
from .obtainings_hgss import trade_catalog
from .offer_rules_hgss import resolve_quantity_rules
from .presence_characters_hgss import attach_presence
from .pret_gen4_source import c_defines
from .pret_hgss_battles import resolved_battles
from .pret_hgss_field_items import field_item_tables
from .pret_hgss_flow import hgss_flow
from .pret_hgss_flow_context import flow_context
from .pret_hgss_offers import resolved_offers
from .pret_hgss_rematches import rematch_catalog
from .pret_hgss_scripts import battle_sites, read_scripts, script_payload
from .pret_hgss_services import apricorn_catalog, shop_catalog, tutor_catalog
from .pret_hgss_trainers import item_constants, trainer_catalog
from .services_characters_hgss import service_catalog, standard_services
from .shops_hgss import athlete_shop_catalog
from .sources import HGSS_PRET_COMMIT
from .sources_characters_hgss import validate_character_sources


def character_catalog(root: Path) -> dict:
    sources = validate_character_sources(root)
    scripts = read_scripts(root)
    context = flow_context(root)
    flows = {bank: hgss_flow(script, context) for bank, script in scripts.items()}
    trainers = trainer_catalog(root)
    raw = battle_sites(scripts, c_defines(root / "include/constants/trainers.h", "TRAINER_"))
    initial = actor_catalog(root, scripts, raw, field_item_tables(root, scripts))
    banks = {actor["bank"] for actor in initial["actors"]}
    offers = resolve_quantity_rules(resolved_offers(flows, banks))
    actors = actor_catalog(root, scripts, raw, field_item_tables(root, scripts), offers)
    battles = resolved_battles(flows)
    missing = bind_battles(actors["actors"], battles, trainers, scripts)
    if missing:
        raise ValueError(f"HGSS : combats sans acteur unique : {missing}")
    _correct_actor_teams(actors["actors"], battles)
    curate_actors(actors["actors"], trainers, offers)
    standard_services(actors["actors"])
    attach_presence(actors["actors"], flows, context.constants)
    _link_offers(offers, actors["actors"])
    rematches = rematch_catalog(root, {row["id"] for row in trainers})
    phone_gifts = _phone_gifts(root, rematches)
    return dict(
        schema=2,
        commit=HGSS_PRET_COMMIT,
        versions=["heartgold", "soulsilver"],
        status="resolved",
        native_sources=sources,
        trainers=trainers,
        battles=raw,
        resolved_battles=battles,
        rematches=rematches,
        calendar=calendar_catalog(root, rematches, flows, trainers, actors["actors"]),
        **actors,
        shops=shop_catalog(root),
        athlete_shops=athlete_shop_catalog(root),
        tutors=tutor_catalog(root),
        apricorns=apricorn_catalog(root),
        trades=trade_catalog(root),
        services=service_catalog(root),
        phone_gifts=phone_gifts,
        service_steps=offers,
        names=native_names(root),
        scripts={str(bank): script_payload(script) for bank, script in scripts.items()},
    )


def _phone_gifts(root: Path, rematches: dict) -> list[dict]:
    items = item_constants(root)
    return [
        dict(
            contact=contact["id"],
            quantity=1,
            candidates=list(range(items["ITEM_CHERI_BERRY"], items["ITEM_CHERI_BERRY"] + 10))
            if contact["gift"] == "ITEM_CHERI_BERRY"
            else [items[contact["gift"]]],
            conditions_fr=["Numéro enregistré", "Cadeau annoncé et en attente", "Parler au contact"],
            source="src/scrcmd_c.c",
            contact_source=contact["source"],
        )
        for contact in rematches["contacts"]
        if contact["gift"] != "ITEM_NONE"
    ]


def _correct_actor_teams(actors: list[dict], battles: list[dict]) -> None:
    bindings: dict[tuple[int, int], set[int]] = {}
    for battle in battles:
        for binding in battle["actors"]:
            bindings.setdefault((binding["header"], binding["event"]), set()).add(binding["trainer"])
            binding["role"] = (
                "partner" if any(v["partner"] == binding["trainer"] for v in battle["variants"]) else "opponent"
            )
    for actor in actors:
        if actor["link"] == "script_graph":
            actor["trainers"] = sorted(bindings.get((actor["header"], actor["event"]), set()))


def _link_offers(offers: list[dict], actors: list[dict]) -> None:
    currencies = ("money", "coins", "battle_points", "athlete_points")
    for index, offer in enumerate(offers):
        offer["id"] = index
        offer["conditions_fr"] = translate_conditions(offer["conditions"])
        offer["actors"] = [
            dict(header=a["header"], event=a["event"], visibility=a["native"]["flag"])
            for a in actors
            if a["bank"] == offer["bank"] and offer["instruction"] in a["service_steps"] and not a["alias_of"]
        ]
        offer["costs"] = [
            dict(currency=currency, amount=amount)
            for currency, amount in zip(currencies, offer["payments"][:4], strict=True)
            if amount != 0
        ]
        item, quantity = offer["payments"][4:]
        if item != 0:
            offer["costs"].append(dict(currency="item", item=item, amount=quantity))
