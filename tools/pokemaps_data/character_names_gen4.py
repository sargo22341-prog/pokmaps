"""Noms français des classes de dresseurs et des personnages DS, relus dans tools/data/.

Les deux dépôts DS n'ont pas les mêmes constantes (TRAINER_CLASS_ACE_TRAINER_MALE en Platine,
TRAINER_CLASS_ACE_TRAINER_M en Diamant/Perle) et certaines reprennent celles des jeux GBA avec un autre nom français
(TRAINER_CLASS_PICNICKER : « Pique-Nique » en 4e génération). Leurs lignes de trainer_classes.csv et npc_names.csv
sont donc préfixées par le dépôt : « pokeplatinum:TRAINER_CLASS_LASS ». Les personnages se nomment d'après leur
apparence : constante OBJ_EVENT_GFX_… de Platine, SPRITE_… de Diamant/Perle (include/constants/sprites.h, où pret
écrit aussi SPRTIE_SUNGLASSES), ou numéro quand ce dépôt ne nomme pas l'apparence.

Les apparences variables (OBJ_EVENT_GFX_VAR_0 à VAR_F en Platine, 101 à 117 dans FieldSystem_ResolveObjectSpriteID
de Diamant/Perle) sont choisies par les scripts : elles prennent le nom commun DYNAMIC_CHARACTER.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .maps_characters_data import CharacterNames
from .pret_gen4_engine_text import c_function
from .pret_gen4_source import c_defines, metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header
    from .pret_gen4_offers import OfferCatalog

DYNAMIC = "DYNAMIC_CHARACTER"
_DP_DYNAMIC = re.compile(r"if \(spriteId >= (\d+) && spriteId <= (\d+)\)")
_FACILITIES = {
    "heal": "heal_spot",
    "daycare": "day_care",
    "daycare_egg": "day_care",
    "daycare_withdrawal": "day_care",
    "move_tutor": "move_tutor",
    "move_relearner": "move_relearner",
    "move_deleter": "move_deleter",
    "point_prize": "battle_point_exchange",
    "prize_item": "prize_vendor",
    "fossil": "fossil_revival",
    "accessory_shop": "accessory_shop",
    "sale_seal": "seal_shop",
    "scratch_cards": "scratch_cards",
}


@dataclass(frozen=True)
class Gen4Names:
    classes: dict[str, str]  # constante de classe -> nom français
    sprites: dict[int, tuple[str, str]]  # apparence employée -> nom français, apparence (person, object, pokemon)
    characters: dict[str, str] = field(default_factory=dict)
    facilities: dict[str, str] = field(default_factory=dict)


def repo_name(repo: Gen4PretRepo) -> str:
    return "pokeplatinum" if repo.platinum else "pokediamond"


def sprite_keys(repo: Gen4PretRepo) -> dict[int, str]:
    """Clé de npc_names.csv de chaque apparence nommée par le dépôt."""
    if repo.platinum:
        values = metang_enum(repo.root / "generated/object_events_gfx.txt")
    else:
        path = repo.root / "include/constants/sprites.h"
        values = {**c_defines(path, "SPRITE_"), **c_defines(path, "SPRTIE_")}
    keys: dict[int, str] = {}
    for name, value in values.items():
        if value in keys:
            raise ValueError(f"{repo.root} : apparence {value} nommée deux fois ({keys[value]}, {name})")
        keys[value] = name
    return keys


def dynamic_sprites(repo: Gen4PretRepo) -> range:
    """Apparences remplacées par le moteur selon une variable des scripts."""
    if repo.platinum:
        values = metang_enum(repo.root / "generated/object_events_gfx.txt")
        body = c_function(
            read_text(repo.root / "src/map_object.c"), "MapObject_GetFieldSystemGraphicsID", "map_object.c"
        )
        if "graphicsID >= OBJ_EVENT_GFX_VAR_0 && graphicsID <= OBJ_EVENT_GFX_VAR_F" not in body:
            raise ValueError(f"{repo.root} : apparences variables modifiées (MapObject_GetFieldSystemGraphicsID)")
        return range(values["OBJ_EVENT_GFX_VAR_0"], values["OBJ_EVENT_GFX_VAR_F"] + 1)
    body = c_function(
        read_text(repo.root / "arm9/src/map_object.c"), "FieldSystem_ResolveObjectSpriteID", "map_object.c"
    )
    found = _DP_DYNAMIC.search(body)
    if found is None:
        raise ValueError(f"{repo.root} : apparences variables modifiées (FieldSystem_ResolveObjectSpriteID)")
    return range(int(found.group(1)), int(found.group(2)) + 1)


def sprite_key(repo: Gen4PretRepo, keys: dict[int, str], dynamic: range, graphics: int) -> str:
    if graphics in dynamic:
        return DYNAMIC
    return f"{repo_name(repo)}:{keys.get(graphics, graphics)}"


def read_gen4_names(
    repo: Gen4PretRepo, headers: dict[int, Gen4Header], names: CharacterNames, offers: OfferCatalog
) -> Gen4Names:
    """Noms de toutes les classes du dépôt et des apparences des personnages posés dans les lieux retenus ; un nom
    manquant arrête la lecture."""
    prefix = repo_name(repo)
    classes = {
        trainer.trainer_class: names.trainer(f"{prefix}:{trainer.trainer_class}") for trainer in repo.trainers.values()
    }
    keys, dynamic = sprite_keys(repo), dynamic_sprites(repo)
    used = {obj.graphics for index in headers for obj in repo.events[headers[index].events].object_events}
    sprites = {}
    for graphics in sorted(used):
        key = sprite_key(repo, keys, dynamic, graphics)
        sprites[graphics] = (names.character(key), names.appearances[key])
    characters = {}
    for index, header in sorted(headers.items()):
        for rank, _obj in enumerate(repo.events[header.events].object_events):
            key = f"{prefix}:{index}:{rank}"
            if key in names.by_text:
                if names.text_families[key] != ("platinum" if repo.platinum else "diamond-pearl"):
                    raise ValueError(f"npc_text_names.csv : famille DS incompatible : {key}")
                characters[key] = names.text_name(key)
    kinds = {offer.kind for step in offers.steps for offer in step.offers}
    facilities = {kind: names.facility(_FACILITIES[kind]) for kind in sorted(kinds & _FACILITIES.keys())}
    return Gen4Names(dict(sorted(classes.items())), sprites, characters, facilities)


def unused_names(names: CharacterNames, found: dict[str, Gen4Names], repos: dict[str, Gen4PretRepo]) -> list[str]:
    """Lignes préfixées par un dépôt DS qu'aucune classe ni aucun personnage de ce dépôt n'emploie."""
    used: set[str] = set()
    for group, catalog in found.items():
        repo = repos[group]
        prefix = repo_name(repo)
        used |= {f"{prefix}:{trainer_class}" for trainer_class in catalog.classes}
        keys, dynamic = sprite_keys(repo), dynamic_sprites(repo)
        used |= {sprite_key(repo, keys, dynamic, graphics) for graphics in catalog.sprites}
        used |= set(catalog.characters)
    prefixes = tuple(f"{repo_name(repo)}:" for repo in repos.values())
    declared = {key for key in (*names.trainers, *names.characters, *names.by_text) if key.startswith(prefixes)}
    return sorted(declared - used)
