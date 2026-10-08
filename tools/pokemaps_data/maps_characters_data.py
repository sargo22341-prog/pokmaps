"""Données relues à la main sur les personnages des cartes (tools/data/).

- trainer_classes.csv, npc_names.csv, npc_text_names.csv, facility_names.csv : noms français des dresseurs (par
  classe), des personnages (par sprite, ou par personnage pour ceux dessinés avec un sprite commun) et des
  installations, et apparence des personnages (une personne, un objet du décor ou un Pokémon) ;
- npc_duplicates.csv : exemplaires d'un même personnage à écarter (un par étape du scénario) ;
- npc_offers.csv : offres que les scripts ne disent pas simplement.

Un personnage y est désigné par sa clé (`character_key`) : la constante de son texte en 1re génération
(TEXT_PALLETTOWN_OAK), la constante de l'objet en 2e (KURTSHOUSE_KURT1), où plusieurs objets partagent un script.
Une ligne qui ne sert à aucun personnage des jeux générés de sa famille arrête la génération.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field

from .pret_models import MapObject, NpcOffer
from .sources import DATA_DIR

# Apparence d'un personnage d'après son sprite (npc_names.csv) -> type de l'objet de carte : une personne, un objet
# du décor qui parle ou donne quelque chose (Fossile, Poké Ball, rocher…), ou un Pokémon qui n'est pas à combattre.
NPC_KINDS = {"person": "npc", "object": "npc_object", "pokemon": "npc_pokemon"}

# Offres ajoutées à la main (npc_offers.csv, action add) : un échange remplace le don du même objet lu dans le
# script ; les Pokémon de départ de Rouge et Bleu sont choisis par un script propre au labo du Prof. Chen ; le
# moteur donne seul le Caratroc prêté à Irisia et la première Ball de Fargas.
CURATED_KINDS = frozenset({"exchange", "coin_sale", "gift_pokemon", "gift_item"})
# Actions de npc_offers.csv : ajouter une offre, ou retirer une offre lue dans le script du personnage alors
# qu'un autre la fait pendant la scène (Peter donne la CS Siphon après les Électrode du QG Rocket).
ADD, REMOVE = "add", "remove"


def character_key(obj: MapObject) -> str | None:
    """Ce qui désigne le personnage dans tools/data/ : constante de l'objet, sinon constante de son texte."""
    return obj.const or obj.text


@dataclass(frozen=True)
class CharacterNames:
    """Noms affichés des dresseurs (par classe), des personnages (par sprite, ou par clé pour un personnage unique
    dessiné avec un sprite commun : Léo a celui d'un Intello) et des installations (par type, ou par clé : le lit
    du M/S Aquaria), et apparence des personnages (par sprite)."""

    trainers: dict[str, str]
    characters: dict[str, str]
    facilities: dict[str, str] = field(default_factory=dict)
    by_text: dict[str, str] = field(default_factory=dict)
    appearances: dict[str, str] = field(default_factory=dict)
    # Famille de cartes de chaque personnage nommé par sa clé (npc_text_names.csv).
    text_families: dict[str, str] = field(default_factory=dict)

    def trainer(self, trainer_class: str) -> str:
        if trainer_class not in self.trainers:
            raise ValueError(f"Classe de dresseur sans nom français : {trainer_class} (tools/data/trainer_classes.csv)")
        return self.trainers[trainer_class]

    def character(self, sprite: str | None) -> str:
        if sprite not in self.characters:
            raise ValueError(f"Personnage sans nom français : sprite {sprite} (tools/data/npc_names.csv)")
        return self.characters[sprite]

    def npc_kind(self, sprite: str | None) -> str:
        """Type d'objet de carte d'un personnage d'après son apparence (npc, npc_object ou npc_pokemon)."""
        appearance = self.appearances.get(sprite or "")
        if appearance not in NPC_KINDS:
            raise ValueError(f"Apparence inconnue pour le sprite {sprite} : {appearance} (tools/data/npc_names.csv)")
        return NPC_KINDS[appearance]

    def facility(self, kind: str) -> str:
        if kind not in self.facilities:
            raise ValueError(f"Installation sans nom français : {kind} (tools/data/facility_names.csv)")
        return self.facilities[kind]


def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_character_names() -> CharacterNames:
    """Noms français des classes de dresseurs, des personnages (d'après leur sprite) et des installations."""
    characters = _read_csv("npc_names.csv")
    texts = _read_csv("npc_text_names.csv")
    return CharacterNames(
        {row["trainer_class"]: row["name_fr"] for row in _read_csv("trainer_classes.csv")},
        {row["sprite"]: row["name_fr"] for row in characters},
        {row["kind"]: row["name_fr"] for row in _read_csv("facility_names.csv")},
        {row["text"]: row["name_fr"] for row in texts},
        {row["sprite"]: row["appearance"] for row in characters},
        {row["text"]: row["family"] for row in texts},
    )


@dataclass(frozen=True)
class CuratedOffer:
    repos: frozenset[str]  # dépôts pret concernés (pokered, pokeyellow, pokegold)
    text: str  # clé du personnage (character_key)
    action: str  # add ou remove
    offer: NpcOffer  # constantes pret


@dataclass
class CharacterCuration:
    """Doublons écartés (npc_duplicates.csv) et offres relues à la main (npc_offers.csv).

    Une ligne qui ne correspond à aucun personnage des jeux générés arrête la génération (`unused`)."""

    duplicates: dict[str, str]  # clé du personnage -> famille de cartes
    offers: list[CuratedOffer]
    used: set[str] = field(default_factory=set)

    def offers_for(self, repo_name: str, text: str | None) -> list[NpcOffer]:
        """Offres ajoutées au personnage."""
        found = [curated.offer for curated in self._rows(repo_name, text) if curated.action == ADD]
        if found:
            self.used.add(f"offre:{repo_name}:{text}")
        return found

    def without_removed(self, repo_name: str, text: str | None, offers: list[NpcOffer]) -> list[NpcOffer]:
        """Offres lues dans le script du personnage, sans celles qu'un autre fait (même type, objet et Pokémon).
        Une offre à retirer que le script ne fait pas arrête la génération."""
        removed = [curated.offer for curated in self._rows(repo_name, text) if curated.action == REMOVE]
        if not removed:
            return offers
        self.used.add(f"retrait:{repo_name}:{text}")
        for offer in removed:
            if not any(_same_offer(offer, read) for read in offers):
                raise ValueError(f"npc_offers.csv : {text} ne fait pas l'offre à retirer {offer}")
        return [read for read in offers if not any(_same_offer(offer, read) for offer in removed)]

    def _rows(self, repo_name: str, text: str | None) -> list[CuratedOffer]:
        return [curated for curated in self.offers if text and curated.text == text and repo_name in curated.repos]

    def is_duplicate(self, text: str | None) -> bool:
        if text in self.duplicates:
            self.used.add(f"doublon:{text}")
            return True
        return False

    def unused(self, families: set[str], repos: set[str]) -> list[str]:
        """Lignes inemployées : doublons des familles `families`, offres des dépôts `repos` (jeux générés)."""
        expected = {f"doublon:{text}" for text, family in self.duplicates.items() if family in families}
        for curated in self.offers:
            prefix = "offre" if curated.action == ADD else "retrait"
            expected |= {f"{prefix}:{repo}:{curated.text}" for repo in curated.repos if repo in repos}
        return sorted(expected - self.used)


def _same_offer(first: NpcOffer, second: NpcOffer) -> bool:
    return (first.kind, first.item, first.pokemon) == (second.kind, second.item, second.pokemon)


def read_character_curation() -> CharacterCuration:
    duplicates = {row["text"]: row["family"] for row in _read_csv("npc_duplicates.csv")}
    offers = []
    for row in _read_csv("npc_offers.csv"):
        if row["action"] not in (ADD, REMOVE) or (row["action"] == ADD and row["kind"] not in CURATED_KINDS):
            raise ValueError(f"npc_offers.csv : action ou type d'offre non pris en charge : {row}")
        offer = NpcOffer(
            row["kind"],
            item=row["item"] or None,
            pokemon=row["pokemon"] or None,
            quantity=int(row["quantity"]) if row["quantity"] else None,
            price=int(row["price"]) if row["price"] else None,
            wanted_item=row["wanted_item"] or None,
        )
        offers.append(CuratedOffer(frozenset(row["repos"].split("|")), row["text"], row["action"], offer))
    return CharacterCuration(duplicates, offers)
