"""Objets ramassables GBA : position, quantité et drapeau de retrait conservés."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_conditions import script_states
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_script_values import number_value
from .pret_gen3_scripts import Gen3Scripts

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo
    from .pret_gen3_offers import Gen3Offers


@dataclass(frozen=True)
class Gen3MapItem:
    map_const: str
    version: str
    kind: str
    x: int
    y: int
    elevation: int
    item: str
    quantity: int
    removal_flag: str
    script: str | None
    underfoot: bool = False


def read_map_items(repo: Gen3PretRepo, version: str) -> tuple[Gen3MapItem, ...]:
    reader = repo.offers[version]
    return tuple(item for current in repo.maps.values() for item in map_items(current, version, reader))


def map_items(current: Gen3Map, version: str, reader: Gen3Offers) -> tuple[Gen3MapItem, ...]:
    # Les carrés de la Pyramide sont des modèles assemblés par le C, sans emplacement fixe dans le monde.
    if current.const.startswith("MAP_BATTLE_PYRAMID_SQUARE"):
        return ()
    result = []
    for event in current.objects:
        if event.value("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL" and (item := _ball(current, event, version, reader)):
            result.append(item)
    for event in current.bg_events:
        if event.kind == "hidden_item":
            result.append(_hidden(current, event, version, reader.scripts))
    return tuple(result)


def _ball(current: Gen3Map, event: Gen3Event, version: str, reader: Gen3Offers) -> Gen3MapItem | None:
    label = str(event.value("script"))
    if label in {"NULL", "0", "0x0"}:
        return None  # Balls du décor des salles de concours, sans interaction.
    result = reader.read(label)
    # Le Terhal de Pierre est dessiné dans une Ball, mais relève des dons de Pokémon.
    kinds = {offer.kind for offer in result.offers}
    if "gift_pokemon" in kinds and kinds <= {"gift_pokemon", "rename_pokemon"}:
        return None
    if not kinds and _wild_battle(reader.scripts, label):
        return None
    result.require_resolved(label)
    if not kinds:
        return None  # Ball du rival : le dialogue ne donne aucun objet.
    gifts = {(offer.item, offer.quantity) for offer in result.offers if offer.kind == "gift_item"}
    if len(gifts) != 1 or any(offer.kind != "gift_item" for offer in result.offers):
        raise ValueError(f"{current.const}, {label} : contenu de Poké Ball ambigu : {result.offers}")
    if any(any(path for path in offer.paths) for offer in result.offers):
        raise ValueError(f"{current.const}, {label} : contenu de Poké Ball conditionnel à relire")
    item, quantity = next(iter(gifts))
    return _item(current, event, version, "item", item or "", quantity or "1", reader.scripts, label)


def _wild_battle(scripts: Gen3Scripts, label: str) -> bool:
    return any(
        instruction is not None and instruction.command == "setwildbattle"
        for state in script_states(scripts, label)
        for instruction in (scripts.instruction(state.point),)
    )


def _hidden(current: Gen3Map, event: Gen3Event, version: str, scripts: Gen3Scripts) -> Gen3MapItem:
    fields = dict(event.fields)
    item = str(event.value("item"))
    if item == "ITEM_NONE" and "EventScript_TryPickUpHiddenCoins" not in scripts.blocks:
        raise ValueError(f"{current.const} : jetons cachés sans script du moteur")
    kind = "hidden_coins" if item == "ITEM_NONE" else "hidden_item"
    return _item(current, event, version, kind, item, str(fields.get("quantity", 1)), scripts, None)


def _item(
    current: Gen3Map,
    event: Gen3Event,
    version: str,
    kind: str,
    item: str,
    quantity: str,
    scripts: Gen3Scripts,
    label: str | None,
) -> Gen3MapItem:
    flag = str(event.value("flag"))
    count = number_value(quantity, scripts.constants)
    if not item.startswith("ITEM_") or (not scripts.constants.get(item) and kind != "hidden_coins"):
        raise ValueError(f"{current.const} : objet ramassable inconnu : {item}")
    if not flag.startswith("FLAG_") or not scripts.constants.get(flag):
        raise ValueError(f"{current.const}, {item} : drapeau de retrait absent ou inconnu : {flag}")
    if count is None or not 1 <= count <= 999:
        raise ValueError(f"{current.const}, {item} : quantité invalide : {quantity}")
    if not 0 <= event.x < current.width or not 0 <= event.y < current.height:
        raise ValueError(f"{current.const}, {item} : position hors carte : {event.x}, {event.y}")
    underfoot = dict(event.fields).get("underfoot", False)
    if type(underfoot) is not bool:
        raise ValueError(f"{current.const}, {item} : propriété underfoot invalide : {underfoot}")
    return Gen3MapItem(
        current.const, version, kind, event.x, event.y, event.elevation, item, count, flag, label, underfoot
    )
