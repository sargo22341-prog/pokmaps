"""Tables de la 2e génération que lisent les offres des personnages : prix des objets, boutiques, échanges en jeu
et arbres à baies (pokegold, data/items et data/events).

Chaque table est lue entière et vérifiée contre ses constantes : une entrée en trop ou en moins arrête la lecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_source import macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo

# Fin d'une liste d'objets dans marts.asm et bargain_shop.asm.
_END = "-1"
_NO_ITEM = "NO_ITEM"
# Macros qui déclarent une CT ou une CS dans item_constants.asm, et préfixe de la constante qu'elles définissent.
_MACHINE_PREFIXES = {"add_tm": "TM_", "add_hm": "HM_"}


@dataclass(frozen=True)
class NpcTrade:
    """Échange en jeu (data/events/npc_trades.asm) : Pokémon demandé, Pokémon donné et objet qu'il tient."""

    wanted: str
    given: str
    item: str | None


def item_prices(repo: Gen2PretRepo) -> dict[str, int]:
    """Objet (constante pret, CT et CS comprises) -> prix en boutique (data/items/attributes.asm).

    La table suit les numéros des objets à partir de 1 (MASTER_BALL)."""
    items = _item_order(repo)[1:]
    prices = [
        parse_int(macro_args(line, "item_attribute")[0])
        for line in source_lines(repo.path("data/items/attributes.asm"))
        if line.startswith("item_attribute ")
    ]
    if len(prices) < len(items):
        raise ValueError(f"{repo.root.name} : {len(prices)} prix pour {len(items)} objets dans attributes.asm")
    return dict(zip(items, prices, strict=False))


def _item_order(repo: Gen2PretRepo) -> list[str]:
    """Objets dans l'ordre de leur numéro (NO_ITEM = 0) : les constantes de item_constants.asm, où les CT et CS
    (add_tm, add_hm) s'intercalent avec des emplacements vides (ITEM_C3…). Les corps de macros sont ignorés."""
    result = []
    in_macro = False
    for line in source_lines(repo.path("constants/item_constants.asm")):
        command = line.split()[0]
        if command in ("MACRO", "ENDM"):
            in_macro = command == "MACRO"
        elif in_macro:
            continue
        elif command == "const":
            result.append(line.split()[1])
        elif command in _MACHINE_PREFIXES:
            result.append(f"{_MACHINE_PREFIXES[command]}{line.split()[1]}")
    if not result or result[0] != _NO_ITEM:
        raise ValueError(f"{repo.root.name} : item_constants.asm ne commence pas par {_NO_ITEM}")
    return result


def marts(repo: Gen2PretRepo) -> dict[str, list[str]]:
    """Boutique (constante MART_…) -> objets vendus, dans l'ordre (data/items/marts.asm)."""
    consts = [const for const in repo.consts("constants/mart_constants.asm") if const.startswith("MART_")]
    lines = source_lines(repo.path("data/items/marts.asm"))
    labels = [macro_args(line, "dw")[0] for line in lines if line.startswith("dw ")]
    if len(labels) != len(consts):
        raise ValueError(f"{repo.root.name} : {len(labels)} boutiques pour {len(consts)} constantes MART_")
    return {const: _item_list(lines, label, repo) for const, label in zip(consts, labels, strict=True)}


def _item_list(lines: list[str], label: str, repo: Gen2PretRepo) -> list[str]:
    """Objets de la liste `label:` (« db nombre », puis un « db OBJET » par objet jusqu'à « db -1 »)."""
    start = lines.index(f"{label}:") + 1
    count = parse_int(macro_args(lines[start], "db")[0])
    items = []
    for line in lines[start + 1 :]:
        value = macro_args(line, "db")[0]
        if value == _END:
            break
        items.append(value)
    if len(items) != count:
        raise ValueError(f"{repo.root.name} : {label} annonce {count} objets et en liste {len(items)}")
    return items


def bargain_shop(repo: Gen2PretRepo) -> list[tuple[str, int]]:
    """Objets du marchand de soldes (MARTTYPE_BARGAIN) et leur prix, propre à ce marchand."""
    lines = source_lines(repo.path("data/items/bargain_shop.asm"))
    offers = [(args[0], parse_int(args[1])) for args in (macro_args(line, "dbw") for line in lines if "dbw " in line)]
    count = parse_int(macro_args(lines[lines.index("BargainShopData:") + 1], "db")[0])
    if len(offers) != count:
        raise ValueError(f"{repo.root.name} : bargain_shop.asm annonce {count} objets et en liste {len(offers)}")
    return offers


def npc_trades(repo: Gen2PretRepo) -> dict[str, NpcTrade]:
    """Échange (constante NPC_TRADE_…) -> Pokémon demandé, donné et objet tenu."""
    consts = [const for const in repo.consts("constants/npc_trade_constants.asm") if const.startswith("NPC_TRADE_")]
    rows = [
        macro_args(line, "npctrade")
        for line in source_lines(repo.path("data/events/npc_trades.asm"))
        if line.startswith("npctrade ")
    ]
    if len(rows) != len(consts):
        raise ValueError(f"{repo.root.name} : {len(rows)} échanges pour {len(consts)} constantes NPC_TRADE_")
    # Arguments : dialogue, Pokémon demandé, Pokémon donné, surnom, DV (deux), objet tenu, n° et nom du dresseur…
    return {
        const: NpcTrade(row[1], row[2], None if row[6] == "NO_ITEM" else row[6])
        for const, row in zip(consts, rows, strict=True)
    }


def fruit_trees(repo: Gen2PretRepo) -> dict[str, str]:
    """Arbre (constante FRUITTREE_…) -> baie ou Noigrume qu'il donne (data/items/fruit_trees.asm)."""
    consts = [const for const in repo.consts("constants/script_constants.asm") if const.startswith("FRUITTREE_")]
    items = [
        macro_args(line, "db")[0]
        for line in source_lines(repo.path("data/items/fruit_trees.asm"))
        if line.startswith("db ")
    ]
    if len(items) != len(consts):
        raise ValueError(f"{repo.root.name} : {len(items)} arbres à baies pour {len(consts)} constantes FRUITTREE_")
    return dict(zip(consts, items, strict=True))
