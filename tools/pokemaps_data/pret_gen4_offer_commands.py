"""Commandes de script DS qui donnent, vendent, échangent ou rendent un service, sous un nom commun aux deux jeux.

Platine les nomme par ses macros (asm/macros/scrcmd.inc), dont les paramètres sont vérifiés ; Diamant/Perle par
les fonctions de gScriptCmdTable, dont certaines ne sont pas nommées (ScrCmd_Unk…) : chacune de celles-là est
reconnue par un fragment de son corps dans arm9/src. Chaque commande garde la place de ses arguments utiles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import asm_function, c_function
from .pret_gen4_flow import ADD_COINS, ADD_ITEM
from .pret_gen4_source import read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

GIVE_POKEMON, GIVE_EGG, NPC_TRADE, FOSSIL = "give_pokemon", "give_egg", "npc_trade", "fossil"
MART_COMMON, MART_SPECIALTIES, MART_DECOR, MART_SEAL = "mart_common", "mart_specialties", "mart_decor", "mart_seal"
MART_FRONTIER, ACCESSORY_SHOP = "mart_frontier", "accessory_shop"
PRIZE_TABLE, POINT_TABLE = "prize_table", "point_table"
HEAL, MOVE_DELETER, MOVE_RELEARNER, MOVE_TUTOR, SHARD_TUTOR = (
    "heal",
    "move_deleter",
    "move_relearner",
    "move_tutor",
    "shard_tutor",
)
DAYCARE, DAYCARE_EGG, DAYCARE_WITHDRAWAL = "daycare", "daycare_egg", "daycare_withdrawal"
PAY_MONEY, PAY_COINS, PAY_POINTS, TAKE_ITEM, PAY_SHARDS = (
    "pay_money",
    "pay_coins",
    "pay_points",
    "take_item",
    "pay_shards",
)
# Commandes qui écrivent un objet ou un Pokémon lu dans une table du moteur, que donne ensuite une autre commande.
TABLE_WRITERS = frozenset({FOSSIL, PRIZE_TABLE, POINT_TABLE})
PAYMENTS = frozenset({PAY_MONEY, PAY_COINS, PAY_POINTS, TAKE_ITEM})


@dataclass(frozen=True)
class OfferCommand:
    kind: str
    # Nom de chaque argument utile -> sa place dans Step.arguments ; « output » est la variable qu'écrit une
    # commande de table, les autres sont lus.
    arguments: tuple[tuple[str, int], ...] = ()

    def position(self, name: str) -> int:
        return dict(self.arguments)[name]


_PLATINUM: dict[str, tuple[str, tuple[tuple[str, int], ...], str]] = {
    # macro -> (nature, arguments, paramètres attendus de la macro)
    ADD_ITEM: (ADD_ITEM, (("item", 0), ("quantity", 1)), ""),
    "GivePokemon": (GIVE_POKEMON, (("species", 0), ("level", 1), ("item", 2)), "species, level, heldItem, successVar"),
    "GiveEgg": (GIVE_EGG, (("species", 0),), "species, eggGiverTextId"),
    "InitNPCTrade": (NPC_TRADE, (("trade", 0),), "npcTradeID"),
    "GetSpeciesFromFossil": (FOSSIL, (("output", 0),), "speciesVar, itemVar"),
    "PokeMartCommon": (MART_COMMON, (), "unused=1"),
    "PokeMartSpecialties": (MART_SPECIALTIES, (("mart", 0),), "martID"),
    "PokeMartDecor": (MART_DECOR, (("mart", 0),), "martID"),
    "PokeMartSeal": (MART_SEAL, (("mart", 0),), "martID"),
    "PokeMartFrontier": (MART_FRONTIER, (("mart", 0),), "martID"),
    "ShowAccessoryShop": (ACCESSORY_SHOP, (), ""),
    "GetGameCornerPrizeData": (PRIZE_TABLE, (("output", 1),), "index, item, price"),
    "HealParty": (HEAL, (), ""),
    "ClearPartyMonMoveSlot": (MOVE_DELETER, (), "partySlot, moveSlot"),
    "OpenMoveReminderMenu": (MOVE_RELEARNER, (), "partySlot"),
    "OpenMoveTutorMenu": (MOVE_TUTOR, (("move", 1),), "partySlot, move"),
    "ShowMoveTutorMoveSelectionMenu": (SHARD_TUTOR, (("location", 1),), "partySlot, location, outSelectedOption"),
    "StorePartyMonIntoDaycare": (DAYCARE, (), "partySlot"),
    "GiveEggFromDaycare": (DAYCARE_EGG, (), ""),
    "MoveMonToPartyFromDaycareSlot": (DAYCARE_WITHDRAWAL, (), "destVarSpecies, daycareSlot"),
    ADD_COINS: (ADD_COINS, (("quantity", 0),), ""),
    "RemoveMoney": (PAY_MONEY, (("amount", 0),), "value"),
    "RemoveMoney2": (PAY_MONEY, (("amount", 0),), "valueOrVarID"),
    "SubtractCoins": (PAY_COINS, (("amount", 0),), "valueOrVarID"),
    "RemoveBattlePoints": (PAY_POINTS, (("amount", 0),), "value"),
    "RemoveItem": (TAKE_ITEM, (("item", 0), ("quantity", 1)), "item, count, destVarID"),
    "PayShardCost": (PAY_SHARDS, (), "moveID"),
}
_DIAMOND_PEARL: dict[str, tuple[str, tuple[tuple[str, int], ...]]] = {
    ADD_ITEM: (ADD_ITEM, (("item", 0), ("quantity", 1))),
    "ScrCmd_GiveMon": (GIVE_POKEMON, (("species", 0), ("level", 1), ("item", 2))),
    "ScrCmd_GiveEgg": (GIVE_EGG, (("species", 0),)),
    "ScrCmd_NPCTradeInit": (NPC_TRADE, (("trade", 0),)),
    "ScrCmd_GetFossilPokemon": (FOSSIL, (("output", 0),)),
    "ScrCmd_NormalMart": (MART_COMMON, ()),
    "ScrCmd_SpecialMart": (MART_SPECIALTIES, (("mart", 0),)),
    "ScrCmd_GoodsMart": (MART_DECOR, (("mart", 0),)),
    "ScrCmd_SealsMart": (MART_SEAL, (("mart", 0),)),
    "ScrCmd_AccessoriesShop": (ACCESSORY_SHOP, ()),
    "ScrCmd_GetPrizeItemIdAndCost": (PRIZE_TABLE, (("output", 1),)),
    "ScrCmd_Unk029B": (POINT_TABLE, (("group", 0), ("output", 2))),
    "ScrCmd_HealParty": (HEAL, ()),
    "ScrCmd_ForgetPartyMonMove": (MOVE_DELETER, ()),
    "ScrCmd_Unk0221": (MOVE_RELEARNER, ()),
    "ScrCmd_Unk0224": (MOVE_TUTOR, (("move", 1),)),
    "ScrCmd_Unk01B0": (DAYCARE, ()),
    "ScrCmd_GiveDaycareEgg": (DAYCARE_EGG, ()),
    "ScrCmd_Unk01A4": (DAYCARE_WITHDRAWAL, ()),
    ADD_COINS: (ADD_COINS, (("quantity", 0),)),
    "ScrCmd_TakeMoneyImmediate": (PAY_MONEY, (("amount", 0),)),
    "ScrCmd_TakeMoneyAddress": (PAY_MONEY, (("amount", 0),)),
    "ScrCmd_TakeCoinsImmediate": (PAY_COINS, (("amount", 0),)),
    "ScrCmd_TakeCoinsAddress": (PAY_COINS, (("amount", 0),)),
    "ScrCmd_Unk0299": (PAY_POINTS, (("amount", 0),)),
    "ScrCmd_TakeItem": (TAKE_ITEM, (("item", 0), ("quantity", 1))),
}
# Fonctions de Diamant/Perle sans nom : fichier et fragments de leur corps qui fixent leur rôle.
_DP_BODIES = {
    "ScrCmd_Unk0221": ("arm9/src/scrcmd_move_relearner.c", ("MoveRelearner_GetEligibleLevelUpMoves", "(ctx, 1,")),
    "ScrCmd_Unk0224": ("arm9/src/scrcmd_move_relearner.c", ("u16 move = ScriptGetVar(ctx);", "= move;", "(ctx, 0,")),
    "ScrCmd_Unk01B0": ("arm9/src/scrcmd_daycare.c", ("ov05_021EC57C(party, (u8)idx, daycare, save);",)),
    "ScrCmd_Unk01A4": (
        "arm9/src/scrcmd_daycare.c",
        ("u16 *ret_ptr = ScriptGetVarPointer(ctx);", "ov05_021EC71C(party"),
    ),
}
_DP_ASM = {
    "ScrCmd_Unk029B": ("arm9/asm/scrcmd_10.s", ("mov r1, #0x1a", "ldr r1, _02042B04", "ldr r1, _02042B08")),
    "ScrCmd_Unk0299": (
        "arm9/asm/scrcmd_10.s",
        ("bl Save_FrontierData_Get", "mov r2, #0x6", "bl FrontierData_BattlePointAction"),
    ),
}


def offer_commands(repo: Gen4PretRepo) -> dict[str, OfferCommand]:
    """Commandes d'offre du dépôt, par nom de commande du flux (pret_gen4_flow)."""
    if repo.platinum:
        macros = read_text(repo.root / "asm/macros/scrcmd.inc")
        for name, (_, _, parameters) in _PLATINUM.items():
            if name in {ADD_ITEM, ADD_COINS}:
                continue
            if not re.search(rf"^\s*\.macro {name}\s*{re.escape(parameters)}\s*$", macros, re.MULTILINE):
                raise ValueError(f"{repo.root} : macro {name} absente ou modifiée")
        return {name: OfferCommand(kind, arguments) for name, (kind, arguments, _) in _PLATINUM.items()}
    names = {command.name for command in repo.script_commands}
    if missing := sorted(set(_DIAMOND_PEARL) - names - {ADD_ITEM, ADD_COINS}):
        raise ValueError(f"{repo.root} : commandes d'offre absentes : {missing}")
    for name, (relative, fragments) in _DP_BODIES.items():
        body = " ".join(c_function(read_text(repo.root / relative), name, relative).split())
        if any(fragment not in body for fragment in fragments):
            raise ValueError(f"{repo.root} : fonction {name} modifiée")
    for name, (relative, fragments) in _DP_ASM.items():
        lines = asm_function(read_text(repo.root / relative), name, relative)
        if any(fragment not in lines for fragment in fragments):
            raise ValueError(f"{repo.root} : fonction {name} modifiée")
    return {name: OfferCommand(kind, arguments) for name, (kind, arguments) in _DIAMOND_PEARL.items()}
