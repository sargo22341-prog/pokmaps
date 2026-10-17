"""Tables du moteur DS lues par les commandes d'offre : boutiques, lots, Points Combat, échanges, tuteurs,
fossiles, prix des objets et niveau des œufs donnés.

Platine les écrit en C ou en JSON (include/data/mart_items.h, src/scrcmd_shop.c, src/overlay007/shop_menu.c,
res/npc_trades, res/pokemon/move_tutors.json, res/items/data) ; Diamant/Perle en C (arm9/src/scrcmd_mart.c,
scrcmd_prizes.c, scrcmd_fossils.c), en binaire (fld_trade, de la forme NPCTradeMon de Platine) et en assembleur
(Points Combat, ScrCmd_Unk029B). Chaque table est relue avec sa fonction quand la forme le permet ; une forme
différente arrête la lecture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import asm_data, asm_function, c_function, c_initializer
from .pret_gen4_narc import members
from .pret_gen4_source import c_defines, c_enum, metang_enum, read_binary, read_json, read_json_list, read_text

if TYPE_CHECKING:
    from pathlib import Path

    from .pret_gen4 import Gen4PretRepo

_END = frozenset({"SHOP_ITEM_END", "0xFFFF"})
_ARRAY = re.compile(r"(?:static\s+)?const\s+u16\s+(\*?)\s*(\w+)\s*\[[^\]]*\]\s*=\s*\{(.*?)\};", re.DOTALL)
_PAIR = re.compile(r"\{\s*(\w+)\s*,\s*(\w+)\s*\}")
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
# Nombre de badges -> palier de la boutique ordinaire (switch de ScrCmd_PokeMartCommon et ScrCmd_NormalMart).
_BADGE_LEVELS = {0: 1, 1: 2, 2: 2, 3: 3, 4: 3, 5: 4, 6: 4, 7: 5, 8: 6}
_TRADE_FIELDS = 20  # NPCTradeMon : vingt entiers de 32 bits (include/overlay006/npc_trade.h)
_TRADE_SPECIES, _TRADE_ITEM, _TRADE_REQUESTED = 0, 15, 19
_DP_POINTS = ("arm9/asm/scrcmd_10.s", "ScrCmd_Unk029B", "UNK_020F433E", "UNK_020F4340")
_DP_POINT_GROUP = 0x1A  # second comptoir : décalage de 26 lignes (mov r1, #0x1a)
_SHARDS = ("redCost", "blueCost", "yellowCost", "greenCost")


@dataclass(frozen=True)
class Trade:
    species: str  # Pokémon reçu
    item: str | None  # objet qu'il tient
    wanted: str  # Pokémon demandé


@dataclass(frozen=True)
class TutorMove:
    move: str
    shards: tuple[tuple[str, int], ...]  # couleur de Tesson -> nombre (rouge, bleu, jaune, vert), sans les zéros


class OfferTables:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo
        self.root = repo.root

    @cached_property
    def item_names(self) -> dict[int, str]:
        if self.repo.platinum:
            values = metang_enum(self.root / "generated/items.txt")
        else:
            values = c_defines(self.root / "include/constants/items.h", "ITEM_")
        return {value: name for name, value in values.items()}

    @cached_property
    def species_names(self) -> dict[int, str]:
        if self.repo.platinum:
            values = metang_enum(self.root / "generated/species.txt")
        else:
            values = c_defines(self.root / "include/constants/species.h", "SPECIES_")
        return {value: name for name, value in values.items()}

    @cached_property
    def move_names(self) -> dict[int, str]:
        if self.repo.platinum:
            values = metang_enum(self.root / "generated/moves.txt")
        else:
            values = c_defines(self.root / "include/constants/moves.h", "MOVE_")
        return {value: name for name, value in values.items()}

    @cached_property
    def prices(self) -> dict[str, int]:
        """Prix en ¥ de chaque objet (paramètre ITEM_PARAM_PRICE des données d'objets)."""
        if self.repo.platinum:
            result = {}
            for name in self.item_names.values():
                path = self.root / f"res/items/data/{name.removeprefix('ITEM_').lower()}.json"
                if path.is_file():
                    result[name] = int(read_json(path)["price"])
            return result
        rows = read_json(self.root / "files/itemtool/itemdata/item_data.json")["item_data"]
        return {row["name"]: int(row["price"]) for row in rows}

    @cached_property
    def common_mart(self) -> tuple[tuple[str, int], ...]:
        """Objets de la boutique ordinaire et nombre minimal de badges pour chacun."""
        if self.repo.platinum:
            text = read_text(self.root / "src/scrcmd_shop.c")
            body = c_function(text, "ScrCmd_PokeMartCommon", "scrcmd_shop.c")
            table = c_initializer(read_text(self.root / "include/data/mart_items.h"), "PokeMartCommonItems", "mart")
        else:
            text = read_text(self.root / "arm9/src/scrcmd_mart.c")
            body = c_function(text, "ScrCmd_NormalMart", "scrcmd_mart.c")
            table = c_initializer(text, "sNormalMartBadgeThresholds", "scrcmd_mart.c")
        _check_badge_levels(body, str(self.root))
        rows = _PAIR.findall(table)
        if not rows or len(rows) != table.count("{"):
            raise ValueError(f"{self.root} : boutique ordinaire illisible")
        return tuple((item, _minimum_badges(int(level, 0), str(self.root))) for item, level in rows)

    @cached_property
    def specialty_marts(self) -> tuple[tuple[str, ...], ...]:
        return self._marts("PokeMartSpecialties", "mart_specialties_id", "sSpecialMartPointers")

    @cached_property
    def decor_marts(self) -> tuple[tuple[str, ...], ...]:
        return self._marts("VeilstoneDeptStoreDecorationStocks", "mart_decor_id", "sDecorationMartPointers")

    @cached_property
    def seal_marts(self) -> tuple[tuple[str, ...], ...]:
        return self._marts("SunyshoreMarketDailyStocks", "mart_seal_id", "sSealsMartPointers")

    def _marts(self, platinum: str, ids: str, diamond_pearl: str) -> tuple[tuple[str, ...], ...]:
        if self.repo.platinum:
            text = read_text(self.root / "include/data/mart_items.h")
            arrays = _arrays(text)
            order = metang_enum(self.root / f"generated/{ids}.txt")
            pointers = dict(re.findall(r"\[(\w+)\]\s*=\s*(\w+)", c_initializer(text, platinum, "mart_items.h")))
            if set(pointers) != set(order):
                raise ValueError(f"{self.root} : boutiques {platinum} incomplètes")
            names = [pointers[name] for name, _ in sorted(order.items(), key=lambda pair: pair[1])]
        else:
            text = read_text(self.root / "arm9/src/scrcmd_mart.c")
            arrays = _arrays(text)
            names = arrays.get(diamond_pearl, [])
        if not names or any(name not in arrays for name in names):
            raise ValueError(f"{self.root} : boutiques {platinum} illisibles")
        return tuple(tuple(arrays[name]) for name in names)

    @cached_property
    def frontier_marts(self) -> tuple[tuple[tuple[str, int], ...], ...]:
        """Comptoirs des Points Combat : objet et prix en Points Combat, par comptoir."""
        if self.repo.platinum:
            body = c_function(read_text(self.root / "src/scrcmd.c"), "ScrCmd_PokeMartFrontier", "scrcmd.c")
            arrays = _arrays(body)
            pointers = re.search(r"BattleFrontierExchangeServiceCorners\[\]\s*=\s*\{(.*?)\};", body, re.DOTALL)
            menu = c_function(read_text(self.root / "src/overlay007/shop_menu.c"), "Shop_GetItemBPPrice", "shop")
            prices = {item: int(price, 0) for item, price in _PAIR.findall(menu)}
            if pointers is None:
                raise ValueError(f"{self.root} : comptoirs des Points Combat illisibles")
            names = [name.strip() for name in pointers.group(1).split(",") if name.strip()]
            return tuple(tuple((item, _price(prices, item, str(self.root))) for item in arrays[name]) for name in names)
        return self._dp_points()

    def _dp_points(self) -> tuple[tuple[tuple[str, int], ...], ...]:
        relative, function, first, second = _DP_POINTS
        text = read_text(self.root / relative)
        lines = asm_function(text, function, relative)
        expected = ("cmp r7, #0x1", f"mov r1, #{_DP_POINT_GROUP:#x}", "add r1, r1, r6", "lsl r2, r1, #0x2")
        if any(line not in lines for line in expected) or f"{first}: ; 0x020F433E" not in text:
            raise ValueError(f"{self.root / relative} : table des Points Combat modifiée")
        if f"{second}: ; 0x020F4340" not in text:
            raise ValueError(f"{self.root / relative} : table des Points Combat non contiguë")
        data = asm_data(text, first, relative) + asm_data(text, second, relative)
        rows = [
            (int.from_bytes(data[at : at + 2], "little"), int.from_bytes(data[at + 2 : at + 4], "little"))
            for at in range(0, len(data) - 3, 4)
        ]
        # La donnée suivante est alignée sur 4 octets : le reste éventuel n'est que du remplissage nul.
        padding = data[len(rows) * 4 :]
        if (
            any(padding)
            or len(rows) <= _DP_POINT_GROUP
            or any(not item or item not in self.item_names for item, _ in rows)
        ):
            raise ValueError(f"{self.root / relative} : table des Points Combat illisible")
        named = tuple((self.item_names[item], price) for item, price in rows)
        return named[:_DP_POINT_GROUP], named[_DP_POINT_GROUP:]

    @cached_property
    def prizes(self) -> tuple[tuple[str, int], ...]:
        """Lots du Casino de Voilaroc : objet et prix en jetons, dans l'ordre de leur numéro."""
        if self.repo.platinum:
            text = read_text(self.root / "src/scrcmd_game_corner_prize.c")
            body = c_function(text, "ScrCmd_GetGameCornerPrizeData", "scrcmd_game_corner_prize.c")
            table = c_initializer(body, "sGameCornerPrizeData", "scrcmd_game_corner_prize.c")
        else:
            table = c_initializer(read_text(self.root / "arm9/src/scrcmd_prizes.c"), "gGameCornerPrizes", "prizes")
        rows = _PAIR.findall(table)
        if not rows or len(rows) != table.count("{"):
            raise ValueError(f"{self.root} : lots du Casino illisibles")
        return tuple((item, int(price, 0)) for item, price in rows)

    @cached_property
    def fossils(self) -> tuple[tuple[str, str], ...]:
        """Fossile -> Pokémon ranimé (sFossilItemToSpeciesMapping, gFossilPokemonMap)."""
        if self.repo.platinum:
            table = c_initializer(read_text(self.root / "src/scrcmd_fossil.c"), "sFossilItemToSpeciesMapping", "")
            rows = re.findall(r"\{\s*\.item\s*=\s*(\w+),\s*\.species\s*=\s*(\w+)\s*\}", table)
        else:
            table = c_initializer(read_text(self.root / "arm9/src/scrcmd_fossils.c"), "gFossilPokemonMap", "fossils")
            rows = _PAIR.findall(table)
        if not rows or len(rows) != table.count("{"):
            raise ValueError(f"{self.root} : table des fossiles illisible")
        return tuple(rows)

    @cached_property
    def egg_level(self) -> int:
        """Niveau d'un œuf donné par GiveEgg (Egg_CreateEgg, ov05_SetEggStats)."""
        if self.repo.platinum:
            body = c_function(read_text(self.root / "src/scrcmd_party.c"), "ScrCmd_GiveEgg", "scrcmd_party.c")
            match = re.search(r"Egg_CreateEgg\(egg, species, (\d+),", body)
        else:
            body = c_function(read_text(self.root / "arm9/src/scrcmd_party.c"), "ScrCmd_GiveEgg", "scrcmd_party.c")
            match = re.search(r"ov05_SetEggStats\(egg, species, (\d+),", body)
        if match is None:
            raise ValueError(f"{self.root} : niveau des œufs donnés illisible")
        return int(match.group(1))

    @cached_property
    def trades(self) -> tuple[Trade, ...]:
        if self.repo.platinum:
            order = c_enum(self.root / "include/constants/npc_trades.h", "NPCTradeID")
            result = []
            for name, index in sorted(order.items(), key=lambda pair: pair[1]):
                if name == "MAX_NPC_TRADES":
                    continue
                if index != len(result):
                    raise ValueError(f"{self.root} : numéros d'échange non consécutifs : {name}")
                data = read_json(self.root / f"res/npc_trades/{name.removeprefix('NPC_TRADE_').lower()}.json")
                item = data["heldItem"] if data["heldItem"] != "ITEM_NONE" else None
                result.append(Trade(data["species"], item, data["requestedSpecies"]))
            return tuple(result)
        files = members(self.root / "files/fielddata/pokemon_trade/fld_trade")
        return tuple(self._dp_trade(files[index]) for index in sorted(files))

    def _dp_trade(self, path: Path) -> Trade:
        data = read_binary(path, 4 * _TRADE_FIELDS)
        if len(data) != 4 * _TRADE_FIELDS:
            raise ValueError(f"{path} : échange de {len(data)} octets, {4 * _TRADE_FIELDS} attendus")
        fields = [int.from_bytes(data[at : at + 4], "little") for at in range(0, len(data), 4)]
        species, item, wanted = fields[_TRADE_SPECIES], fields[_TRADE_ITEM], fields[_TRADE_REQUESTED]
        if species not in self.species_names or wanted not in self.species_names or item not in self.item_names:
            raise ValueError(f"{path} : échange illisible")
        held = self.item_names[item] if item else None
        return Trade(self.species_names[species], held, self.species_names[wanted])

    @cached_property
    def tutors(self) -> dict[str, tuple[TutorMove, ...]]:
        """Attaques des tuteurs de Platine par lieu (TUTOR_LOCATION_…), avec leur prix en Tessons."""
        if not self.repo.platinum:
            return {}
        result: dict[str, list[TutorMove]] = {}
        for row in read_json_list(self.root / "res/pokemon/move_tutors.json"):
            shards = tuple((color.removesuffix("Cost"), int(row[color])) for color in _SHARDS if int(row[color]))
            if not shards:
                raise ValueError(f"{self.root} : attaque de tuteur sans prix : {row['move']}")
            result.setdefault(row["location"], []).append(TutorMove(row["move"], shards))
        return {location: tuple(moves) for location, moves in result.items()}


def _arrays(text: str) -> dict[str, list[str]]:
    """Tableaux C de u16 (objets jusqu'à SHOP_ITEM_END ou 0xFFFF, ou pointeurs vers d'autres tableaux)."""
    result = {}
    for pointer, name, body in _ARRAY.findall(_COMMENT.sub("", text)):
        tokens = [token.strip() for token in body.split(",") if token.strip()]
        if not pointer:
            if not tokens or tokens[-1] not in _END or any(token in _END for token in tokens[:-1]):
                raise ValueError(f"tableau {name} sans fin de boutique")
            tokens = tokens[:-1]
        result[name] = tokens
    return result


def _check_badge_levels(body: str, where: str) -> None:
    cases = re.findall(r"case (\d+):\s*(?:case (\d+):\s*)?\w+ = (\d+);", body)
    levels = {}
    for first, second, level in cases:
        for count in (first, second):
            if count:
                levels[int(count)] = int(level)
    if levels != _BADGE_LEVELS:
        raise ValueError(f"{where} : paliers de la boutique ordinaire modifiés : {levels}")


def _minimum_badges(level: int, where: str) -> int:
    counts = [count for count, reached in _BADGE_LEVELS.items() if reached >= level]
    if not counts:
        raise ValueError(f"{where} : palier de boutique inaccessible : {level}")
    return min(counts)


def _price(prices: dict[str, int], item: str, where: str) -> int:
    if item not in prices:
        raise ValueError(f"{where} : objet sans prix en Points Combat : {item}")
    return prices[item]
