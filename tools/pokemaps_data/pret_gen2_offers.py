"""Offres des personnages et des installations de la 2e génération, lues dans leurs scripts d'événements.

Un script est lu bloc par bloc (pret_gen2_scripts.ScriptFile.reachable_blocks), version par version (checkver) :

- « giveitem » / « verbosegiveitem » : objet donné ; vendu si le bloc prend de l'argent (takemoney ou checkmoney :
  distributeurs, Lait Meumeu, Bonbon Rage) ; lot du Casino si le bloc prend des jetons (takecoins) ;
- « givepoke » : Pokémon donné, avec l'objet qu'il tient, ou lot du Casino ; « giveegg » : œuf donné ;
- « trade » : échange en jeu ; « pokemart » : boutique ; « fruittree » : arbre à baies ou à Noigrumes ;
- « givecoins » : jetons donnés, ou vendus si le bloc prend de l'argent ;
- « special » : service rendu (soins, pension, Club Link…), offre que fait le moteur seul et que relit
  tools/data/npc_offers.csv (Caratroc prêté à Irisia, Balls de Fargas), ou rien. Une commande special qui n'est dans
  aucune de ces listes arrête la lecture : elle doit être classée ;
- « jumpstd » / « callstd » : le script commun appelé (engine/events/std_scripts.asm) est lu de la même façon
  (infirmière des Centres Pokémon, vendeur de jetons).

Une offre lue dans toutes les versions du jeu n'a pas de version ; sinon elle porte celle où elle existe (lots du
Casino de Doublonville : Abo dans Or, Sabelette dans Argent).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import cached_property
from typing import TYPE_CHECKING

from .pret_crystal_offers import NO_OFFER_SPECIALS as CRYSTAL_NO_OFFER_SPECIALS
from .pret_crystal_offers import buena_prizes, move_tutor_price, odd_eggs, rooftop_sales
from .pret_gen2_conditions import Gen2Conditions, Point
from .pret_gen2_offer_data import NpcTrade, bargain_shop, fruit_trees, item_prices, marts, npc_trades
from .pret_gen2_scripts import ScriptFile
from .pret_models import NpcOffer, merged_offers
from .pret_services import version_offers
from .pret_source import macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo

# Services rendus par les commandes special (engine/events/specials.asm).
HEAL, CABLE_CLUB, NAME_RATER, DAYCARE = "heal", "cable_club", "name_rater", "daycare"
MOVE_DELETER, GROOMING = "move_deleter", "grooming"
SERVICE_KINDS = frozenset({HEAL, CABLE_CLUB, NAME_RATER, DAYCARE, MOVE_DELETER, GROOMING, "move_tutor"})
SPECIAL_SERVICES = {
    "MoveTutor": "move_tutor",
    "HealParty": HEAL,
    "NameRater": NAME_RATER,
    "DayCareMan": DAYCARE,
    "DayCareLady": DAYCARE,
    "DayCareManOutside": DAYCARE,
    "MoveDeletion": MOVE_DELETER,
    # Hôtesses du Club Link : échanges, combats et Capsule Temporelle.
    "SetBitsForLinkTradeRequest": CABLE_CLUB,
    "SetBitsForBattleRequest": CABLE_CLUB,
    "SetBitsForTimeCapsuleRequest": CABLE_CLUB,
    # Toilettage qui rend un Pokémon plus heureux : frères coiffeurs du Souterrain, sœur du Rival à Bourg Palette.
    "OlderHaircutBrother": GROOMING,
    "YoungerHaircutBrother": GROOMING,
    "DaisysGrooming": GROOMING,
}
# Offres que fait le moteur sans les écrire dans le script : le personnage doit en avoir dans npc_offers.csv.
CURATED_SPECIALS = frozenset(
    {
        "GiveShuckle",  # Caratroc prêté à Irisia (engine/events/shuckle.asm)
        "SelectApricornForKurt",  # Noigrume choisi par Fargas, rendu en Ball le lendemain
    }
)
# Commandes special sans offre : effets d'écran et de musique, jeux du Casino, consoles et contrôles du Club Link,
# questions sur l'équipe, scènes, et ce qui n'est pas une offre de la carte (Banque de Maman réglée au Pokématos,
# Cadeau Mystère entre deux consoles, diplôme et photo souvenir, Train Magnétique, impression des Zarbi).
NO_OFFER_SPECIALS = frozenset(
    {
        "BankOfMom",
        "BillsGrandfather",
        "CardFlip",
        "CheckBothSelectedSameRoom",
        "CheckFirstMonIsEgg",
        "CheckForLuckyNumberWinners",
        "CheckLinkTimeout_Receptionist",
        "CheckLuckyNumberShowFlag",
        "CheckMagikarpLength",
        "CheckPokerus",
        "CheckTimeCapsuleCompatibility",
        "CloseLink",
        "Colosseum",
        "ContestDropOffMons",
        "Diploma",
        "DisplayCoinCaseBalance",
        "DisplayLinkRecord",
        "DisplayMoneyAndCoinBalance",
        "EnterTimeCapsule",
        "FadeInFromBlack",
        "FadeInFromWhite",
        "FadeOutMusic",
        "FadeOutToBlack",
        "FadeOutToWhite",
        "FailedLinkToPast",
        "FindPartyMonThatSpecies",
        "FindPartyMonThatSpeciesYourTrainerID",
        "GameboyCheck",
        "GameCornerPrizeMonCheckDex",
        "GetFirstPokemonHappiness",
        "GetMysteryGiftItem",
        "GiveParkBalls",
        "HealMachineAnim",
        "LoadUsedSpritesGFX",
        "MagikarpHouseSign",
        "MapRadio",
        "MagnetTrain",
        "NameRival",
        "PhotoStudio",
        "PlaceMoneyTopRight",
        "PlayCurMonCry",
        "PlayMapMusic",
        "PlaySlowCry",
        "PlayersHousePC",
        "PrintDiploma",
        "PrintTodaysLuckyNumber",
        "ProfOaksPCBoot",
        "ReloadSpritesNoPalettes",
        "ResetLuckyNumberShowFlag",
        "RestartMapMusic",
        "ReturnShuckie",
        "SelectRandomBugContestContestants",
        "SlotMachine",
        "SnorlaxAwake",
        "TimeCapsule",
        "TradeCenter",
        "TryQuickSave",
        "UnlockMysteryGift",
        "UnownPrinter",
        "UnownPuzzle",
        "UpdateSprites",
        "WaitForLinkedFriend",
        "WaitForOtherPlayerToExit",
    }
)
# Boutiques aux prix de la table des objets, et marchand de soldes du Souterrain, qui a ses propres prix.
_PRICED_MARTS = frozenset({"MARTTYPE_STANDARD", "MARTTYPE_BITTER", "MARTTYPE_PHARMACY"})
_BARGAIN_MART = "MARTTYPE_BARGAIN"
_NO_ITEM = "NO_ITEM"
_STD_CALLS = frozenset({"jumpstd", "callstd"})


@dataclass(frozen=True)
class ScriptOffers:
    """Offres lues dans un script, et commandes special dont l'offre est relue dans npc_offers.csv."""

    offers: tuple[NpcOffer, ...]
    curated_specials: frozenset[str]
    # Drapeaux et objets que le script lève, baisse, montre ou cache lui-même (Gen2Conditions.own_flags).
    own: frozenset[str] = frozenset()
    # Lignes que le script peut exécuter (pret_gen2_conditions.Point), toutes versions réunies.
    points: frozenset[Point] = frozenset()


class Gen2Offers:
    """Lecteur des offres d'un dépôt pret de la 2e génération (tables lues une fois)."""

    def __init__(self, repo: Gen2PretRepo) -> None:
        self.repo = repo

    @cached_property
    def prices(self) -> dict[str, int]:
        return item_prices(self.repo)

    @cached_property
    def marts(self) -> dict[str, list[str]]:
        return marts(self.repo)

    @cached_property
    def bargain_shop(self) -> list[tuple[str, int]]:
        return bargain_shop(self.repo)

    @cached_property
    def trades(self) -> dict[str, NpcTrade]:
        return npc_trades(self.repo)

    @cached_property
    def fruit_trees(self) -> dict[str, str]:
        return fruit_trees(self.repo)

    @cached_property
    def std_scripts(self) -> ScriptFile:
        return ScriptFile(self.repo.path("engine/events/std_scripts.asm"))

    @cached_property
    def conditions(self) -> Gen2Conditions:
        """Lecteur des conditions, sur les mêmes scripts communs que les offres (les points en dépendent)."""
        return Gen2Conditions(self.std_scripts)

    @cached_property
    def constants(self) -> dict[str, int]:
        """Constantes numériques des fichiers constants/ (EGG_LEVEL…)."""
        result = {}
        for path in sorted(self.repo.path("constants").glob("*.asm")):
            for line in source_lines(path):
                parts = line.split()
                if len(parts) == 4 and parts[0] == "DEF" and parts[2] == "EQU" and _is_number(parts[3]):
                    result[parts[1]] = parse_int(parts[3])
        return result

    def script_offers(self, script_file: ScriptFile, label: str) -> ScriptOffers:
        """Offres du script `label` de `script_file`, dans l'ordre où le script les fait."""
        by_version: dict[str, list[NpcOffer]] = {}
        curated: set[str] = set()
        own: set[str] = set()
        points: set[Point] = set()
        for version, symbol in self.repo.versions:
            read = self._version_offers(script_file, label, self.repo.checkver(symbol))
            by_version[version] = list(read.offers)
            curated |= read.curated_specials
            own |= read.own
            points |= read.points
        return ScriptOffers(tuple(version_offers(by_version)), frozenset(curated), frozenset(own), frozenset(points))

    def _version_offers(self, script_file: ScriptFile, label: str, checkver: bool) -> ScriptOffers:
        """Offres et commandes special à relire, en suivant les scripts communs appelés (chacun une fois). Chaque
        offre porte ce qu'exige le chemin du script qui y mène (pret_gen2_conditions)."""
        points = self.conditions.script_conditions(script_file, label, checkver)
        own = self.conditions.own_flags(points)
        pending = [(script_file, label)]
        seen = {label}
        offers: list[NpcOffer] = []
        curated: set[str] = set()
        while pending:
            source, name = pending.pop(0)
            for block_name, lines in source.reachable_named_blocks(name, checkver):
                block = _Block(self, source, lines)
                for index, offer in block.offers():
                    condition = points.get((source, block_name, index))
                    if condition is None:
                        raise ValueError(f"{source.path.name} : offre {offer} hors des chemins analysés ({block_name})")
                    offers.append(replace(offer, condition=condition.without(own)))
                curated |= block.curated_specials()
                for std in block.std_calls():
                    if std not in seen:
                        seen.add(std)
                        pending.append((self.std_scripts, std))
        return ScriptOffers(tuple(merged_offers(offers)), frozenset(curated), own, frozenset(points))


def _is_number(value: str) -> bool:
    return value.isdigit() or (value.startswith("$") and all(c in "0123456789abcdefABCDEF" for c in value[1:]))


class _Block:
    """Un bloc de script : ses lignes, et l'argent ou les jetons qu'il prend (prix de ce qu'il donne)."""

    def __init__(self, reader: Gen2Offers, source: ScriptFile, lines: list[str]) -> None:
        self.reader = reader
        self.source = source
        self.lines = lines
        self.coins = self._price(("takecoins",), 0)
        self.money = self._price(("takemoney", "checkmoney"), 1)

    def value(self, text: str) -> int:
        """Nombre écrit ou constante (du fichier, puis de constants/)."""
        if _is_number(text):
            return parse_int(text)
        for constants in (self.source.constants, self.reader.constants):
            if text in constants:
                return constants[text]
        raise ValueError(f"{self.source.path.name} : constante inconnue {text}")

    def _price(self, commands: tuple[str, ...], position: int) -> int | None:
        """Montant que prend le bloc (argument `position` de l'une des `commands`), None s'il ne prend rien."""
        values = {
            self.value(macro_args(line, command)[position])
            for line in self.lines
            for command in commands
            if line.startswith(f"{command} ")
        }
        if len(values) > 1:
            raise ValueError(f"{self.source.path.name} : plusieurs montants dans un même bloc : {sorted(values)}")
        return next(iter(values), None)

    def offers(self) -> list[tuple[int, NpcOffer]]:
        """Offres du bloc, chacune avec le rang de la ligne qui la fait."""
        result: list[tuple[int, NpcOffer]] = []
        for index, line in enumerate(self.lines):
            command, _, rest = line.partition(" ")
            if command in _HANDLERS:
                result += [(index, offer) for offer in _HANDLERS[command](self, macro_args(rest, ""))]
        return result

    def curated_specials(self) -> set[str]:
        return {name for name in self._specials() if name in CURATED_SPECIALS}

    def std_calls(self) -> list[str]:
        return [line.split()[1] for line in self.lines if line.split()[0] in _STD_CALLS]

    def _specials(self) -> list[str]:
        return [line.split()[1] for line in self.lines if line.startswith("special ")]

    def where(self) -> str:
        return self.source.path.name


def _items(block: _Block, args: list[str]) -> list[NpcOffer]:
    item = args[0]
    if block.coins is not None:
        return [NpcOffer("prize_item", item=item, price=block.coins)]
    if block.money is not None:
        return [NpcOffer("sale", item=item, price=block.money)]
    return [NpcOffer("gift_item", item=item, quantity=block.value(args[1]) if len(args) > 1 else 1)]


def _pokemon(block: _Block, args: list[str]) -> list[NpcOffer]:
    pokemon, level = args[0], block.value(args[1])
    held = args[2] if len(args) > 2 and args[2] != _NO_ITEM else None
    if block.coins is not None:
        if held:
            raise ValueError(f"{block.where()} : lot {pokemon} tenant un objet, non pris en charge")
        return [NpcOffer("prize_pokemon", pokemon=pokemon, quantity=level, price=block.coins)]
    if block.money is not None:
        raise ValueError(f"{block.where()} : Pokémon {pokemon} vendu contre de l'argent, non pris en charge")
    return [NpcOffer("gift_pokemon", item=held, pokemon=pokemon, quantity=level)]


def _egg(block: _Block, args: list[str]) -> list[NpcOffer]:
    return [NpcOffer("gift_egg", pokemon=args[0], quantity=block.value(args[1]))]


def _trade(block: _Block, args: list[str]) -> list[NpcOffer]:
    trade = block.reader.trades.get(args[0])
    if trade is None:
        raise ValueError(f"{block.where()} : échange inconnu {args[0]}")
    return [NpcOffer("trade", item=trade.item, pokemon=trade.given, wanted=trade.wanted)]


def _mart(block: _Block, args: list[str]) -> list[NpcOffer]:
    mart_type, mart = args[0], args[1]
    if mart_type == "MARTTYPE_ROOFTOP":
        return rooftop_sales(block.reader.repo)
    if mart_type == _BARGAIN_MART:
        return [NpcOffer("sale", item=item, price=price) for item, price in block.reader.bargain_shop]
    if mart_type not in _PRICED_MARTS or mart not in block.reader.marts:
        raise ValueError(f"{block.where()} : boutique non prise en charge : {mart_type}, {mart}")
    return [NpcOffer("sale", item=item, price=block.reader.prices[item]) for item in block.reader.marts[mart]]


def _fruit_tree(block: _Block, args: list[str]) -> list[NpcOffer]:
    if args[0] not in block.reader.fruit_trees:
        raise ValueError(f"{block.where()} : arbre à baies inconnu {args[0]}")
    return [NpcOffer("fruit_tree", item=block.reader.fruit_trees[args[0]])]


def _coins(block: _Block, args: list[str]) -> list[NpcOffer]:
    coins = block.value(args[0])
    if block.money is not None:
        return [NpcOffer("coin_sale", quantity=coins, price=block.money)]
    return [NpcOffer("coin_gift", quantity=coins)]


def _special(block: _Block, args: list[str]) -> list[NpcOffer]:
    name = args[0]
    if name == "GiveOddEgg":
        return odd_eggs(block.reader.repo)
    if name == "BuenaPrize":
        return buena_prizes(block.reader.repo)
    if name in SPECIAL_SERVICES:
        service = SPECIAL_SERVICES[name]
        price = (
            move_tutor_price(block.source) if service == "move_tutor" else block.money if service == GROOMING else None
        )
        return [NpcOffer(service, price=price)]
    if name in CURATED_SPECIALS or name in NO_OFFER_SPECIALS or name in CRYSTAL_NO_OFFER_SPECIALS:
        return []
    raise ValueError(f"{block.where()} : commande special non classée : {name} (pret_gen2_offers)")


_HANDLERS: dict[str, Callable[[_Block, list[str]], list[NpcOffer]]] = {
    "giveitem": _items,
    "verbosegiveitem": _items,
    "givepoke": _pokemon,
    "giveegg": _egg,
    "trade": _trade,
    "pokemart": _mart,
    "fruittree": _fruit_tree,
    "givecoins": _coins,
    "special": _special,
}
