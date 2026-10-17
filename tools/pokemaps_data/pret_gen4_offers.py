"""Offres des lieux DS : dons, œufs, boutiques, échanges, tuteurs, services, fossiles, Pension et Casino.

Chaque point de départ d'un lieu (pret_gen4_offer_sites) mène à des commandes d'offre (pret_gen4_offer_reader),
traduites ici avec les tables du moteur (pret_gen4_offer_tables). Un don précédé d'un paiement devient une vente
(argent), un lot (jetons, Points Combat) ou un échange d'objet (objet repris) ; des jetons payés en argent sont
une vente de jetons. Les conditions sont celles qui valent sur tous les chemins du point de départ jusqu'à
l'offre (pret_gen4_flow_requirements), sans les drapeaux que le script lève lui-même (« déjà donné ») ; un drapeau
du jour (DAILY_FLAGS_START à DAILY_FLAGS_END, remis à zéro chaque jour) qui doit être baissé fait une offre
quotidienne. La version du jeu est portée par l'offre, pas par ses conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import asm_function
from .pret_gen4_flow import ADD_COINS, ADD_ITEM, GAME_VERSION, SET_FLAG, Value, reachable
from .pret_gen4_flow_chains import Condition
from .pret_gen4_flow_requirements import requirements_at
from .pret_gen4_offer_bundles import ItemBundle, item_bundles
from .pret_gen4_offer_commands import (
    ACCESSORY_SHOP,
    DAYCARE,
    DAYCARE_EGG,
    DAYCARE_WITHDRAWAL,
    FOSSIL,
    GIVE_EGG,
    GIVE_POKEMON,
    HEAL,
    MART_COMMON,
    MART_DECOR,
    MART_FRONTIER,
    MART_SEAL,
    MART_SPECIALTIES,
    MOVE_DELETER,
    MOVE_RELEARNER,
    MOVE_TUTOR,
    NPC_TRADE,
    PAY_SHARDS,
    POINT_TABLE,
    PRIZE_TABLE,
    SHARD_TUTOR,
    TAKE_ITEM,
)
from .pret_gen4_offer_reader import FoundOffer, OfferReader
from .pret_gen4_offer_rewards import scratch_rewards
from .pret_gen4_offer_sites import OfferSite, offer_sites
from .pret_gen4_offer_tables import OfferTables
from .pret_gen4_source import metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header

_SERVICES = {
    HEAL: "heal",
    MOVE_DELETER: "move_deleter",
    DAYCARE: "daycare",
    DAYCARE_EGG: "daycare_egg",
    DAYCARE_WITHDRAWAL: "daycare_withdrawal",
    ACCESSORY_SHOP: "accessory_shop",
}
_DP_DAILY = ("arm9/asm/unk_02038C78.s", "sub_0203959C")
_DP_DAILY_LINES = ("mov r1, #0xaa", "lsl r1, r1, #0x4", "bl Save_VarsFlags_GetFlagAddr", "mov r2, #0x18")
_DP_DAILY_START, _DP_DAILY_BYTES = 0xAA0, 0x18


@dataclass(frozen=True)
class Gen4Offer:
    kind: str
    item: str | None = None  # objet donné, vendu, échangé ou gagné ; fossile ranimé ; décoration ou sceau vendu
    pokemon: str | None = None
    quantity: int | None = None  # nombre d'objets ou de jetons ; niveau du Pokémon donné, de l'œuf ou du fossile
    price: int | None = None
    currency: str | None = None  # money, coins, battle_points ou shards (None : argent d'une boutique)
    wanted: str | None = None  # Pokémon demandé (échange)
    wanted_item: str | None = None  # objet repris (échange d'objet, Maître des Capacités)
    move: str | None = None
    shards: tuple[tuple[str, int], ...] = ()  # Tessons demandés par un tuteur de Platine
    badges: int | None = None  # nombre de badges à partir duquel la boutique ordinaire vend l'objet
    versions: tuple[str, ...] = ()  # versions où l'offre existe ; vide pour toutes celles du jeu
    wanted_quantity: int | None = None
    extra_items: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class OfferStep:
    site: OfferSite
    step: str  # commande (et appels de scripts communs) qui fait l'offre
    offers: tuple[Gen4Offer, ...]
    conditions: tuple[Condition, ...]  # conditions nécessaires, avant traduction (story_conditions_gen4)
    daily: bool


@dataclass(frozen=True)
class OfferCatalog:
    steps: tuple[OfferStep, ...]
    # Événements dont le numéro de script dépasse la table du fichier (pret_gen4_offer_sites).
    outside_scripts: tuple[str, ...]


def read_offers(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> OfferCatalog:
    builder = _Builder(repo)
    steps: list[OfferStep] = []
    outside: list[str] = []
    for index in sorted(headers):
        sites, unreadable = offer_sites(repo, headers[index])
        outside += unreadable
        for site in sites:
            steps += builder.site(site)
    return OfferCatalog(tuple(steps), tuple(outside))


def daily_flags(repo: Gen4PretRepo) -> range:
    """Drapeaux remis à zéro chaque jour (FieldSystem_ClearDailyFlags de Platine, sub_0203959C de Diamant/Perle)."""
    if repo.platinum:
        values = metang_enum(repo.root / "generated/vars_flags.txt")
        return range(values["DAILY_FLAGS_START"], values["DAILY_FLAGS_END"] + 1)
    lines = asm_function(read_text(repo.root / _DP_DAILY[0]), _DP_DAILY[1], _DP_DAILY[0])
    if any(line not in lines for line in _DP_DAILY_LINES):
        raise ValueError(f"{repo.root} : remise à zéro des drapeaux du jour modifiée ({_DP_DAILY[1]})")
    return range(_DP_DAILY_START, _DP_DAILY_START + 8 * _DP_DAILY_BYTES)


class _Builder:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo
        self.reader = OfferReader(repo)
        self.tables = OfferTables(repo)
        self.daily = daily_flags(repo)
        self._cache: dict[
            tuple[int, int], tuple[tuple[str, tuple[Gen4Offer, ...], tuple[Condition, ...], bool], ...]
        ] = {}

    def site(self, site: OfferSite) -> list[OfferStep]:
        key = (site.script_file, site.entry)
        if key not in self._cache:
            self._cache[key] = self._entry(*key)
        return [
            OfferStep(site, step, offers, (*site.conditions, *conditions), daily)
            for step, offers, conditions, daily in self._cache[key]
        ]

    def _entry(
        self, file: int, entry: int
    ) -> tuple[tuple[str, tuple[Gen4Offer, ...], tuple[Condition, ...], bool], ...]:
        if self.repo.flows[file].name == "scripts_scratch_off_cards":
            offers = (
                Gen4Offer("scratch_cards", quantity=3, price=1, currency="battle_points"),
                *(Gen4Offer("scratch_prize", item, quantity=count) for item, count in scratch_rewards(self.repo)),
            )
            return (("OpenScratchOffCardsApp", offers, (), False),)
        founds = self.reader.entry(file, entry)
        if not founds:
            return ()
        flow = self.repo.flows[file]
        start = flow.entries[entry]
        keys = {found.key for found in founds}
        requirements = requirements_at(flow, start, lambda step: step.key in keys, self.repo.common_scripts)
        steps = reachable(flow, start)
        own = {flow.steps[key].arguments[0] for key in steps if flow.steps[key].command == SET_FLAG}
        grouped: dict[object, list[FoundOffer]] = {}
        for found in founds:
            grouped.setdefault(found.key, []).append(found)
        result = []
        bundles = item_bundles(flow, self.reader.commands)
        for key, group in grouped.items():
            bundle = next((bundle for bundle in bundles if key in bundle.steps), None)
            if bundle is not None and key != bundle.start:
                continue
            try:
                if bundle is None:
                    offers = sorted({offer for found in group for offer in self._offers(found, founds)}, key=repr)
                else:
                    offers = [self._bundle(bundle, group[0])]
            except ValueError as error:
                raise ValueError(f"{flow.name}, point d'entrée {entry + 1} : {error}") from error
            if not offers:
                continue
            conditions, daily = self._conditions(requirements.get(key, ()), own)
            sources = " ; ".join(dict.fromkeys(found.source for found in group))
            result.append((sources, tuple(offers), conditions, daily))
        return tuple(result)

    def _bundle(self, bundle: ItemBundle, found: FoundOffer) -> Gen4Offer:
        items = tuple((self._item(item, found), count) for item, count in bundle.items)
        return Gen4Offer(
            "exchange",
            items[0][0],
            quantity=items[0][1],
            wanted_item=self._item(bundle.wanted, found),
            wanted_quantity=bundle.quantity,
            extra_items=items[1:],
        )

    def _conditions(self, conditions: tuple[Condition, ...], own: set[Value]) -> tuple[tuple[Condition, ...], bool]:
        kept = []
        # Le script peut lever le drapeau avant de remettre l'objet : l'analyse des
        # conditions l'a alors retiré, mais la remise à zéro quotidienne vaut toujours.
        daily = any(flag in self.daily for flag in own if isinstance(flag, int))
        for condition in conditions:
            kind, _, number = condition.subject.partition(":")
            if condition.subject == GAME_VERSION:
                continue
            if kind == "flag" and int(number) in self.daily and condition.value == 0:
                daily = True
                continue
            if kind == "flag" and int(number) in own:
                continue
            kept.append(condition)
        return tuple(kept), daily

    def _offers(self, found: FoundOffer, siblings: tuple[FoundOffer, ...]) -> list[Gen4Offer]:
        if found.consumes_table:
            return []
        result = []
        names = [name for name, _ in found.command.arguments]
        for combo in found.combos:
            arguments = dict(zip(names, combo[: len(names)], strict=True))
            version, *payments = combo[len(names) :]
            versions = (self.reader.versions[version],) if isinstance(version, int) else ()
            made = self._made(found, arguments, payments, siblings)
            result += [replace(offer, versions=versions) for offer in made]
        return result

    def _made(
        self, found: FoundOffer, arguments: dict[str, Value], payments: list[Value], siblings: tuple[FoundOffer, ...]
    ) -> list[Gen4Offer]:
        kind = found.command.kind
        if kind in _SERVICES:
            return [Gen4Offer(_SERVICES[kind])]
        if kind == PRIZE_TABLE:
            return [Gen4Offer("prize_item", item, price=price, currency="coins") for item, price in self.tables.prizes]
        if kind == FOSSIL:
            level = self._fossil_level(found, siblings)
            return [Gen4Offer("fossil", item, pokemon, level) for item, pokemon in self.tables.fossils]
        if kind == POINT_TABLE:
            return self._shop(found, arguments)
        money, coins, points, taken, taken_quantity = (_payment(value, found) for value in payments)
        if kind == ADD_ITEM:
            item, quantity = self._item(arguments["item"], found), _number(arguments["quantity"], found)
            offer = _paid_item(item, quantity, money, coins, points, self._item(taken, found) if taken else None)
            return [replace(offer, wanted_quantity=taken_quantity if taken else None)]
        if kind == ADD_COINS:
            quantity = _number(arguments["quantity"], found)
            if money:
                return [Gen4Offer("coin_sale", quantity=quantity, price=money, currency="money")]
            return [Gen4Offer("coin_gift", quantity=quantity)]
        if money or coins or points or taken:
            raise ValueError(f"{found.source} : offre {kind} précédée d'un paiement")
        return self._unpaid(found, arguments)

    def _unpaid(self, found: FoundOffer, arguments: dict[str, Value]) -> list[Gen4Offer]:
        kind = found.command.kind
        if kind == GIVE_POKEMON:
            species = self._species(arguments["species"], found)
            held = _number(arguments["item"], found)
            item = self._item(held, found) if held else None
            return [Gen4Offer("gift_pokemon", item, species, _number(arguments["level"], found))]
        if kind == GIVE_EGG:
            species = self._species(arguments["species"], found)
            return [Gen4Offer("gift_egg", pokemon=species, quantity=self.tables.egg_level)]
        if kind == NPC_TRADE:
            trade = self.tables.trades[_index(arguments["trade"], len(self.tables.trades), found)]
            return [Gen4Offer("trade", trade.item, trade.species, wanted=trade.wanted)]
        return self._shop(found, arguments)

    def _shop(self, found: FoundOffer, arguments: dict[str, Value]) -> list[Gen4Offer]:
        kind, tables = found.command.kind, self.tables
        if kind == MART_COMMON:
            return [
                Gen4Offer("sale", item, price=self._price(item, found), badges=badges)
                for item, badges in tables.common_mart
            ]
        if kind == MART_SPECIALTIES:
            mart = tables.specialty_marts[_index(arguments["mart"], len(tables.specialty_marts), found)]
            return [Gen4Offer("sale", item, price=self._price(item, found)) for item in mart]
        if kind in {MART_DECOR, MART_SEAL}:
            marts = tables.decor_marts if kind == MART_DECOR else tables.seal_marts
            sold = "sale_decoration" if kind == MART_DECOR else "sale_seal"
            return [Gen4Offer(sold, item) for item in marts[_index(arguments["mart"], len(marts), found)]]
        if kind in {MART_FRONTIER, POINT_TABLE}:
            name = "mart" if kind == MART_FRONTIER else "group"
            counter = tables.frontier_marts[_index(arguments[name], len(tables.frontier_marts), found)]
            return [Gen4Offer("point_prize", item, price=price, currency="battle_points") for item, price in counter]
        if kind == MOVE_TUTOR:
            return [Gen4Offer("move_tutor", move=self._move(arguments["move"], found))]
        if kind == SHARD_TUTOR:
            return self._shard_tutor(found, arguments["location"])
        if kind == MOVE_RELEARNER:
            return [Gen4Offer("move_relearner", wanted_item=self._relearner_item(found))]
        raise ValueError(f"{found.source} : offre {kind} non traduite")

    def _shard_tutor(self, found: FoundOffer, location: Value) -> list[Gen4Offer]:
        """Tuteur de Platine : la liste ne vaut offre que si un paiement en Tessons la suit (CommonScript_ShardCost…
        n'affiche que les prix)."""
        flow = self.repo.flows[found.file]
        if not any(flow.steps[key].command in self._names(PAY_SHARDS) for key in reachable(flow, found.step)):
            return []
        names = {value: name for name, value in self.repo.constants.items() if name.startswith("TUTOR_LOCATION_")}
        place = (
            location if isinstance(location, str) else names.get(int(location)) if isinstance(location, int) else None
        )
        if place not in self.tables.tutors:
            raise ValueError(f"{found.source} : lieu de tuteur inconnu : {location}")
        return [
            Gen4Offer("move_tutor", move=move.move, currency="shards", shards=move.shards)
            for move in self.tables.tutors[place]
        ]

    def _relearner_item(self, found: FoundOffer) -> str:
        """Objet que reprend le Maître des Capacités après la leçon (RemoveItem, ScrCmd_TakeItem)."""
        flow = self.repo.flows[found.file]
        taken = {
            flow.steps[key].arguments[0]
            for key in reachable(flow, found.step)
            if flow.steps[key].command in self._names(TAKE_ITEM)
        }
        if len(taken) != 1:
            raise ValueError(f"{found.source} : objet repris par le Maître des Capacités illisible : {taken}")
        return self._item(next(iter(taken)), found)

    def _fossil_level(self, found: FoundOffer, siblings: tuple[FoundOffer, ...]) -> int:
        levels = {
            combo[1]
            for sibling in siblings
            if sibling.command.kind == GIVE_POKEMON and sibling.consumes_table and sibling.file == found.file
            for combo in sibling.combos
        }
        if len(levels) != 1 or not isinstance(next(iter(levels)), int):
            raise ValueError(f"{found.source} : niveau du fossile ranimé illisible : {levels}")
        return int(next(iter(levels)))

    def _names(self, kind: str) -> set[str]:
        return {name for name, command in self.reader.commands.items() if command.kind == kind}

    def _item(self, value: Value, found: FoundOffer) -> str:
        number = _number(value, found)
        if number not in self.tables.item_names or not number:
            raise ValueError(f"{found.source} : objet inconnu : {value}")
        return self.tables.item_names[number]

    def _species(self, value: Value, found: FoundOffer) -> str:
        number = _number(value, found)
        if number not in self.tables.species_names or not number:
            raise ValueError(f"{found.source} : Pokémon inconnu : {value}")
        return self.tables.species_names[number]

    def _move(self, value: Value, found: FoundOffer) -> str:
        number = _number(value, found)
        if number not in self.tables.move_names or not number:
            raise ValueError(f"{found.source} : attaque inconnue : {value}")
        return self.tables.move_names[number]

    def _price(self, item: str, found: FoundOffer) -> int:
        if not self.tables.prices.get(item):
            raise ValueError(f"{found.source} : objet vendu sans prix : {item}")
        return self.tables.prices[item]


def _paid_item(item: str, quantity: int, money: int, coins: int, points: int, taken: str | None) -> Gen4Offer:
    if taken:
        return Gen4Offer("exchange", item, quantity=quantity, wanted_item=taken)
    if coins:
        return Gen4Offer("prize_item", item, quantity=quantity, price=coins, currency="coins")
    if points:
        return Gen4Offer("point_prize", item, quantity=quantity, price=points, currency="battle_points")
    if money:
        return Gen4Offer("sale", item, quantity=quantity, price=money, currency="money")
    return Gen4Offer("gift_item", item, quantity=quantity)


def _number(value: Value, found: FoundOffer) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{found.source} : valeur illisible : {value}")
    return value


def _payment(value: Value, found: FoundOffer) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{found.source} : paiement illisible : {value}")
    return value


def _index(value: Value, size: int, found: FoundOffer) -> int:
    number = _number(value, found)
    if not 0 <= number < size:
        raise ValueError(f"{found.source} : numéro hors de la table : {number} (sur {size})")
    return number
