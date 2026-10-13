"""État affiché de Hoenn : héros garçon, rivale fille, introduction terminée."""

from __future__ import annotations

from dataclasses import replace

from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import Gen3Offers, ScriptOffers


def display_event(current: Gen3Map, event: Gen3Event) -> Gen3Event | None:
    fields = dict(event.fields)
    sprite, flag = str(fields["graphics_id"]), str(fields["flag"])
    if (
        sprite in {"OBJ_EVENT_GFX_CAMERAMAN", "OBJ_EVENT_GFX_REPORTER_F"}
        and "GABBY_AND_TY" in flag
        and not flag.endswith("_1")
    ):
        return None  # Les revanches réemploient les deux mêmes acteurs sur la même case.
    if flag.startswith("FLAG_DECORATION_"):
        return None  # Décorations choisies par le joueur, sans apparence ni position prédéfinies.
    if sprite == "OBJ_EVENT_GFX_PROF_BIRCH" and current.label != "LittlerootTown_ProfessorBirchsLab":
        return None
    if current.label == "Route101" and sprite in {
        "OBJ_EVENT_GFX_BIRCHS_BAG",
        "OBJ_EVENT_GFX_POOCHYENA",
        "OBJ_EVENT_GFX_ZIGZAGOON_1",
    }:
        return None
    if current.label == "LittlerootTown" and (
        sprite in {"OBJ_EVENT_GFX_TRUCK", "OBJ_EVENT_GFX_MOM"} or "RIVAL" in flag
    ):
        return None
    if (
        current.label.startswith("LittlerootTown_")
        and "House" in current.label
        and _excluded_house_actor(current, sprite)
    ):
        return None
    if "RIVAL" in flag and sprite == "OBJ_EVENT_GFX_VAR_3":
        return None  # L'acteur à vélo et celui à pied représentent la même scène.
    if "RIVAL" in flag and sprite == "OBJ_EVENT_GFX_VAR_0":
        fields["graphics_id"] = "OBJ_EVENT_GFX_RIVAL_MAY_NORMAL"
    return replace(event, fields=tuple(fields.items()))


def _excluded_house_actor(current: Gen3Map, sprite: str) -> bool:
    if sprite.startswith(("OBJ_EVENT_GFX_MACHOKE_", "OBJ_EVENT_GFX_VIGOROTH_")):
        return True
    if "BrendansHouse" in current.label:
        return sprite in {
            "OBJ_EVENT_GFX_RIVAL_BRENDAN_NORMAL",
            "OBJ_EVENT_GFX_WOMAN_4",
            "OBJ_EVENT_GFX_WOMAN_5",
            "OBJ_EVENT_GFX_NINJA_BOY",
            "OBJ_EVENT_GFX_SWABLU_DOLL",
            "OBJ_EVENT_GFX_ITEM_BALL",
        }
    return sprite == "OBJ_EVENT_GFX_MOM"


def display_result(current: Gen3Map, event: Gen3Event, result: ScriptOffers, reader: Gen3Offers) -> ScriptOffers:
    if current.label not in {"Route110", "Route119"} or "RIVAL" not in str(event.value("flag")):
        return result
    scenes = [
        reader.read(str(dict(trigger.fields)["script"]))
        for trigger in current.coord_events
        if dict(trigger.fields).get("var") == f"VAR_{current.label.upper()}_STATE"
    ]
    trainers = tuple(sorted({trainer for scene in scenes for trainer in scene.trainers}))
    if not trainers or any(not trainer.startswith(("TRAINER_MAY_", "TRAINER_BRENDAN_")) for trainer in trainers):
        raise ValueError(f"{current.label} : combat de la rivale absent ou ambigu")
    offers = tuple(dict.fromkeys(offer for scene in scenes for offer in scene.offers))
    return replace(result, trainers=trainers, offers=tuple(dict.fromkeys((*result.offers, *offers))))
