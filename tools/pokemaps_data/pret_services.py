"""Services des personnages et des installations, lus dans les scripts pret.

Un personnage peut soigner, ranimer un fossile, garder un Pokémon, noter les surnoms, donner des jetons ;
une installation (distributeur, comptoir des lots du Casino) vend des boissons ou échange des jetons contre
des lots. Les lots diffèrent entre Rouge et Bleu : ils sont lus pour chaque version du jeu.
"""

from __future__ import annotations

import re
from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .pret_models import NpcOffer, merged_offers
from .pret_source import conditional_lines, macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret import PretRepo

# Instruction présente dans le texte d'un personnage -> service qu'il rend.
SERVICE_MARKERS: tuple[tuple[str, str], ...] = (
    ("script_pokecenter_nurse", "heal"),
    ("predef HealParty", "heal"),
    ("script_cable_club_receptionist", "cable_club"),
    ("farcall DisplayNameRaterScreen", "name_rater"),
    ("ld a, [wDayCareInUse]", "daycare"),
)
FOSSIL_REVIVAL = "farcall GiveFossilToCinnabarLab"
_COIN_GIFT = re.compile(r"^SetEvent EVENT_GOT_(\d+)_COINS(?:_\d+)?$")

# Installations (panneaux) : macro de leur texte -> type d'installation. Le lit ou la machine de soins (heal_spot)
# n'existe qu'en 2e génération (labo du Prof. Orme, cabines du M/S Aquaria).
VENDING_MACHINE = "vending_machine"
PRIZE_VENDOR = "prize_vendor"
HEAL_SPOT = "heal_spot"
FACILITY_MACROS = {"script_vending_machine": VENDING_MACHINE, "script_prize_vendor": PRIZE_VENDOR}


def character_services(repo: PretRepo, text: str | None) -> list[NpcOffer]:
    """Services rendus par le personnage qui affiche ce texte : soins, Club Link, pension, fossiles, jetons…"""
    located = repo.located_text_body(text)
    body = [line.line for line in located]
    place = repo.conditions.offer_place(text)
    offers = [
        place.where([line for line in located if line.line == marker], NpcOffer(service))
        for marker, service in SERVICE_MARKERS
        if marker in body
    ]
    if FOSSIL_REVIVAL in body:
        revival = [line for line in located if line.line == FOSSIL_REVIVAL]
        offers += [place.where(revival, offer) for offer in fossil_revivals(repo, body)]
    for line in located:
        if match := _COIN_GIFT.match(line.line):
            offers.append(place.at(line, NpcOffer("coin_gift", quantity=int(match.group(1)))))
    return merged_offers(offers)


def fossil_revivals(repo: PretRepo, body: list[str]) -> list[NpcOffer]:
    """Fossiles que ranime le personnage (FossilsList, GiveFossilToCinnabarLab) et niveau du Pokémon rendu."""
    fossils = [arg for line in repo.script_body("FossilsList") for arg in macro_args(line, "db") if arg != "0"]
    pokemon = _revived_pokemon(repo, fossils)
    levels = [parse_int(line.split(",")[1]) for line, after in pairwise(body) if _gives_pokemon(line, after)]
    if len(set(levels)) != 1:
        raise ValueError(f"{repo.root.name} : niveau des fossiles ranimés introuvable ({levels})")
    return [NpcOffer("fossil", item=fossil, pokemon=pokemon[fossil], quantity=levels[0]) for fossil in fossils]


def _gives_pokemon(line: str, after: str) -> bool:
    return line.startswith("ld c, ") and after == "call GivePokemon"


def _revived_pokemon(repo: PretRepo, fossils: list[str]) -> dict[str, str]:
    """Fossile -> Pokémon, d'après les comparaisons de GiveFossilToCinnabarLab (le dernier fossile par défaut)."""
    lines = source_lines(repo.path("engine/events/cinnabar_lab.asm"))
    # Le choix du Pokémon commence à la première comparaison avec un fossile.
    lines = lines[next((i for i, line in enumerate(lines) if line.split()[-1] in fossils), len(lines)) :]
    labels: dict[str, str] = {}  # label de branche -> fossile comparé
    pending = None
    for line in lines:
        if line.startswith("cp "):
            pending = line.split()[1]
        elif line.startswith("jr z, .") and pending:
            labels[line.split()[-1]] = pending
            pending = None
    result: dict[str, str] = {}
    current = next(iter(set(fossils) - set(labels.values())), None) if len(fossils) == len(labels) + 1 else None
    for line in lines:
        if line in labels:
            current = labels[line]
        elif line.startswith("ld b, ") and current and current not in result:
            result[current] = line.split()[-1]
        elif line.startswith(".fossilSelected"):
            break
    if sorted(result) != sorted(fossils):
        raise ValueError(f"{repo.root.name} : Pokémon des fossiles introuvables ({result} pour {fossils})")
    return result


def facility_kind(repo: PretRepo, text: str) -> str | None:
    """Type de l'installation qui affiche ce texte (distributeur, comptoir des lots), None pour un panneau."""
    kinds = {FACILITY_MACROS[line] for line in repo.text_body(text) if line in FACILITY_MACROS}
    if len(kinds) > 1:
        raise ValueError(f"{repo.root.name} : installation ambiguë pour {text} : {kinds}")
    return next(iter(kinds), None)


def vending_offers(repo: PretRepo) -> list[NpcOffer]:
    """Boissons du distributeur et leur prix (data/items/vending_prices.asm)."""
    offers = []
    for line in source_lines(repo.path("data/items/vending_prices.asm")):
        if line.startswith("vend_item "):
            item, price = macro_args(line, "vend_item")
            offers.append(NpcOffer("sale", item=item, price=parse_int(price)))
    if not offers:
        raise ValueError(f"{repo.root.name} : aucune boisson dans vending_prices.asm")
    return offers


def prize_offers(repo: PretRepo, window: int, versions: tuple[tuple[str, str], ...]) -> list[NpcOffer]:
    """Lots du comptoir `window` (0 à 2) du Casino, avec leur prix en jetons et le niveau des Pokémon.

    Un lot propre à une version (ex. Insécateur dans Rouge) porte cette version ; un lot commun n'en a pas."""
    return version_offers({version: _prizes(repo, window, frozenset({symbol})) for version, symbol in versions})


def version_offers(by_version: dict[str, list[NpcOffer]]) -> list[NpcOffer]:
    """Offres de chaque version du jeu réunies : une offre de toutes les versions n'en porte aucune, une offre
    propre à certaines versions est répétée pour chacune d'elles. L'ordre est celui de la première apparition."""
    all_offers = list(dict.fromkeys(offer for offers in by_version.values() for offer in offers))
    result = []
    for offer in all_offers:
        present = [version for version, offers in by_version.items() if offer in offers]
        if len(present) == len(by_version):
            result.append(offer)
        else:
            result += [replace(offer, version=version) for version in present]
    return result


def _prizes(repo: PretRepo, window: int, defined: frozenset[str]) -> list[NpcOffer]:
    lines = conditional_lines(repo.path("data/events/prizes.asm"), defined)
    menus = [macro_args(line, "dw") for line in lines if line.startswith("dw ")]
    if not 0 <= window < len(menus):
        raise ValueError(f"{repo.root.name} : comptoir de lots {window} inconnu ({len(menus)} menus)")
    entries, costs = (_label_values(lines, label) for label in menus[window])
    if len(entries) != len(costs) or not entries:
        raise ValueError(f"{repo.root.name} : lots et prix incohérents dans {menus[window]}")
    species = set(repo.consts("constants/pokemon_constants.asm"))
    levels = _prize_levels(repo, defined)
    offers = []
    for entry, cost in zip(entries, costs, strict=True):
        if entry in species:
            if entry not in levels:
                raise ValueError(f"{repo.root.name} : niveau du lot {entry} introuvable")
            offers.append(NpcOffer("prize_pokemon", pokemon=entry, quantity=levels[entry], price=parse_int(cost)))
        else:
            offers.append(NpcOffer("prize_item", item=entry, price=parse_int(cost)))
    return offers


def _label_values(lines: list[str], label: str) -> list[str]:
    """Valeurs (db / bcd2) qui suivent `label:` jusqu'au marqueur de fin « db "@" »."""
    start = lines.index(f"{label}:") + 1
    values = []
    for line in lines[start:]:
        if line == 'db "@"':
            return values
        values.append(line.split(maxsplit=1)[1])
    raise ValueError(f"prizes.asm : liste {label} non terminée")


def _prize_levels(repo: PretRepo, defined: frozenset[str]) -> dict[str, int]:
    levels = {}
    for line in conditional_lines(repo.path("data/events/prize_mon_levels.asm"), defined):
        if line.startswith("db "):
            pokemon, level = macro_args(line, "db")
            levels[pokemon] = parse_int(level)
    return levels
