"""Validation des noms éditoriaux GBA contre les constantes et scripts des sources épinglées."""

from __future__ import annotations

import re

from .maps_characters_data import CharacterNames, read_character_names
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_source import read_text


def validate_gen3_names(repo: Gen3PretRepo, family: str, names: CharacterNames | None = None) -> None:
    names = names if names is not None else read_character_names()
    definitions = read_text(repo.root / "include/constants/event_objects.h")
    sprites = set(re.findall(r"#define\s+(OBJ_EVENT_GFX_\w+)\s", definitions))
    for sprite in sorted(sprites):
        # Les VAR sont des références de sprites choisis par le moteur, pas des apparences fixes.
        if sprite == "OBJ_EVENT_GFX_VARS" or sprite.startswith("OBJ_EVENT_GFX_VAR_"):
            continue
        names.character(sprite)
        names.npc_kind(sprite)
    for version, _ in repo.versions:
        for trainer in repo.trainers[version].values():
            names.trainer(trainer.trainer_class)
    scripts = {str(event.value("script")) for current in repo.maps.values() for event in current.objects}
    # Rubis/Saphir et Émeraude partagent une famille ; chaque dépôt n'en utilise qu'une partie.
    for key, text_family in names.text_families.items():
        if text_family == family and key in scripts:
            names.text_name(key)
