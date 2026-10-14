"""Dons de scènes relus et rattachés à leur personnage, sans déplacer les récompenses d'un adversaire."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo
    from .pret_models import MapObject, NpcOffer, PretMap

# Ces scènes font parler le donneur mais ne passent pas par son script d'interaction.
_SCENES = {
    "ELMSLAB_ELMS_AIDE": ("AideScript_GivePotion", "AideScript_GiveYouBalls"),
    "MRPOKEMONSHOUSE_GENTLEMAN": ("MrPokemonsHouseMrPokemonEventScript",),
    "DRAGONSDENB1F_CLAIR": ("DragonsDenB1F_ClairScene",),
    "RADIOTOWER5F_DIRECTOR": ("RadioTower5FRocketBossScript",),
}


def scene_gifts(repo: Gen2PretRepo, pret_map: PretMap, obj: MapObject) -> list[NpcOffer]:
    """Lit seulement les objets donnés par la scène ; les soins concernent sa mise en scène."""
    if obj.const == "RADIOTOWER5F_DIRECTOR" and obj.kind == "trainer":
        return []
    if obj.const == "DRAGONSDENB1F_CLAIR" and all(version != "crystal" for version, _ in repo.versions):
        return []
    source = repo.script_files[pret_map.label]
    result = []
    for label in _SCENES.get(obj.const or "", ()):
        if not source.has_label(label):
            raise ValueError(f"{source.path.name} : scène de don absente : {label}")
        for offer in repo.offers.script_offers(source, label).offers:
            if offer.kind != "gift_item":
                continue
            stories = {
                "POTION": ("Après avoir reçu le Pokémon de départ",),
                "POKE_BALL": ("Après avoir remis l’Œuf Mystère au Prof. Orme",),
                "MYSTERY_EGG": ("Première visite chez M. Pokémon",),
                "TM_DRAGONBREATH": ("Après l’épreuve du Maître de l’Antre du Dragon",),
                "CLEAR_BELL": ("Après la libération de la Tour Radio",),
                "RAINBOW_WING": ("Après la libération de la Tour Radio",),
                "SILVER_WING": ("Après la libération de la Tour Radio",),
            }
            if offer.item not in stories:
                raise ValueError(f"{source.path.name} : don de scène à relire : {label}, {offer.item}")
            result.append(replace(offer, stories=stories[offer.item]))
    return result
