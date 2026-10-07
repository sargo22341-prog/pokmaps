"""Personnages, dresseurs, objets et installations des cartes, avec ce qu'ils proposent.

Les objets de carte viennent des object_event pret (personnages, dresseurs, objets, Pokémon fixes) et des
bg_event qui rendent un service (distributeur, comptoir des lots) ; leurs offres viennent des scripts pret
(`pret.py`, `pret_services.py`) et, quand le script ne se lit pas simplement, de tools/data/npc_offers.csv.

Un même personnage apparaît parfois plusieurs fois dans pret, un exemplaire par étape du scénario (le
Prof. Chen qui vient chercher le joueur, puis dans son labo) : tools/data/npc_duplicates.csv écarte ces
doublons pour qu'il n'en reste qu'un, celui avec qui l'on interagit vraiment.

Les offres et installations sont lues pour la 1re génération. Celles de la 2e génération (dons, boutiques,
échanges, arbres à baies, Casino…) le seront avec l'entrée d'Or et Argent dans games.GAMES : d'ici là, ses
personnages sont exportés avec leur position, leur apparence et l'équipe des dresseurs, sans offre.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field

from .games import Game
from .maps_layout import GameMaps, identifier
from .pret import GYM_LEADERS, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_identifiers import item_identifier, species_identifier
from .pret_models import MapObject, NpcOffer, PretMap, Sign
from .pret_services import (
    PRIZE_VENDOR,
    VENDING_MACHINE,
    character_services,
    facility_kind,
    prize_offers,
    vending_offers,
)
from .sources import DATA_DIR

# Classes de dresseurs dont l'équipe dépend du starter choisi (fixée par le script, pas par la carte).
STARTER_DEPENDENT_TRAINERS = frozenset({"RIVAL1", "RIVAL2", "RIVAL3"})

# Offres relues à la main (npc_offers.csv) : un échange remplace le don du même objet lu dans le script. Les
# Pokémon de départ (gift_pokemon) sont choisis par un script propre au labo du Prof. Chen, pas par GivePokemon.
CURATED_KINDS = frozenset({"exchange", "coin_sale", "gift_pokemon"})


@dataclass
class ObjectRow:
    map_const: str
    kind: str  # npc, item, hidden_item, trainer, pokemon, vending_machine ou prize_vendor
    x: int
    y: int
    sprite: str | None
    item: str | None  # identifiant PokéAPI
    pokemon: str | None  # identifiant PokéAPI
    level: int | None
    trainer_class: str | None
    text: str | None = None  # ce qui identifie le personnage dans pret (constante TEXT_… ou label de script)
    # Équipe d'un dresseur : (Pokémon, niveau, attaques), identifiants PokéAPI.
    party: list[tuple[str, int, tuple[str, ...]]] = field(default_factory=list)
    # Dons, ventes, échanges et services (identifiants PokéAPI).
    offers: list[NpcOffer] = field(default_factory=list)
    # Version PokéAPI où l'objet est ainsi (Ho-Oh et Lugia n'ont pas le même niveau en Or et en Argent), None s'il
    # est le même dans toutes les versions du jeu.
    version: str | None = None


# --- Données relues à la main ---------------------------------------------------


# Apparence d'un personnage d'après son sprite (npc_names.csv) -> type de l'objet de carte : une personne, un objet
# du décor qui parle ou donne quelque chose (Fossile, Poké Ball, rocher…), ou un Pokémon qui n'est pas à combattre.
NPC_KINDS = {"person": "npc", "object": "npc_object", "pokemon": "npc_pokemon"}


@dataclass(frozen=True)
class CharacterNames:
    """Noms affichés des dresseurs (par classe), des personnages (par sprite, ou par texte pour un personnage
    unique dessiné avec un sprite commun : Léo a celui d'un Intello) et des installations (par type), et apparence
    des personnages (par sprite)."""

    trainers: dict[str, str]
    characters: dict[str, str]
    facilities: dict[str, str] = field(default_factory=dict)
    by_text: dict[str, str] = field(default_factory=dict)
    appearances: dict[str, str] = field(default_factory=dict)

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
    return CharacterNames(
        {row["trainer_class"]: row["name_fr"] for row in _read_csv("trainer_classes.csv")},
        {row["sprite"]: row["name_fr"] for row in characters},
        {row["kind"]: row["name_fr"] for row in _read_csv("facility_names.csv")},
        {row["text"]: row["name_fr"] for row in _read_csv("npc_text_names.csv")},
        {row["sprite"]: row["appearance"] for row in characters},
    )


@dataclass(frozen=True)
class CuratedOffer:
    repos: frozenset[str]  # dépôts pret concernés (pokered, pokeyellow)
    text: str  # texte du personnage (constante TEXT_…)
    offer: NpcOffer  # constantes pret


@dataclass
class CharacterCuration:
    """Doublons écartés (npc_duplicates.csv) et offres relues à la main (npc_offers.csv).

    Une ligne qui ne correspond à aucun personnage des jeux arrête la génération (`unused`)."""

    duplicates: frozenset[str]
    offers: list[CuratedOffer]
    used: set[str] = field(default_factory=set)

    def offers_for(self, repo_name: str, text: str | None) -> list[NpcOffer]:
        found = [curated.offer for curated in self.offers if curated.text == text and repo_name in curated.repos]
        if found and text:
            self.used.add(f"offre:{repo_name}:{text}")
        return found

    def is_duplicate(self, text: str | None) -> bool:
        if text in self.duplicates:
            self.used.add(f"doublon:{text}")
            return True
        return False

    def unused(self) -> list[str]:
        expected = {f"doublon:{text}" for text in self.duplicates} | {
            f"offre:{repo}:{curated.text}" for curated in self.offers for repo in curated.repos
        }
        return sorted(expected - self.used)


def read_character_curation() -> CharacterCuration:
    duplicates = frozenset(row["text"] for row in _read_csv("npc_duplicates.csv"))
    offers = []
    for row in _read_csv("npc_offers.csv"):
        if row["kind"] not in CURATED_KINDS:
            raise ValueError(f"npc_offers.csv : type d'offre non pris en charge : {row['kind']}")
        offer = NpcOffer(
            row["kind"],
            item=row["item"] or None,
            pokemon=row["pokemon"] or None,
            quantity=int(row["quantity"]) if row["quantity"] else None,
            price=int(row["price"]) if row["price"] else None,
            wanted_item=row["wanted_item"] or None,
        )
        offers.append(CuratedOffer(frozenset(row["repos"].split("|")), row["text"], offer))
    return CharacterCuration(duplicates, offers)


# --- Export -----------------------------------------------------------------------


def object_rows(game_maps: GameMaps, curation: CharacterCuration) -> tuple[list[ObjectRow], set[str]]:
    """Objets de toutes les cartes placées du jeu, et sprites de personnages à exporter."""
    objects: list[ObjectRow] = []
    sprites: set[str] = set()
    for const in sorted(game_maps.placements, key=lambda c: game_maps.maps[c].number):
        pret_map = game_maps.maps[const]
        for obj in pret_map.objects:
            if not (0 <= obj.x < pret_map.width * 2 and 0 <= obj.y < pret_map.height * 2):
                continue  # hors de la carte, donc inaccessible (ex. une Pépite cachée de l'entrée du Parc Safari)
            if curation.is_duplicate(obj.text):
                continue
            if obj.sprite:
                sprites.add(obj.sprite)
            objects.append(_character_row(game_maps, pret_map, obj, curation))
        objects += _facility_rows(game_maps, pret_map)
    return objects, sprites


def _character_row(game_maps: GameMaps, pret_map: PretMap, obj: MapObject, curation: CharacterCuration) -> ObjectRow:
    repo = game_maps.repo
    trainer_class = obj.trainer_class and obj.trainer_class.removeprefix("OPP_")
    party = []
    if trainer_class and trainer_class not in STARTER_DEPENDENT_TRAINERS:
        party = [
            (species_identifier(mon.species), mon.level, tuple(identifier(move) for move in mon.moves))
            for mon in repo.trainer_parties.get((trainer_class, obj.trainer_number or 0), [])
        ]
    offers = _character_offers(game_maps, pret_map, obj, curation)
    return ObjectRow(
        pret_map.const,
        obj.kind,
        *game_maps.point(pret_map.const, obj.x, obj.y),
        obj.sprite and identifier(obj.sprite.removeprefix("SPRITE_")),
        obj.item and item_identifier(obj.item, repo.machines),
        obj.pokemon and species_identifier(obj.pokemon),
        obj.level,
        trainer_class and identifier(trainer_class),
        obj.text,
        party,
        [_offer_identifiers(repo.machines, offer) for offer in dict.fromkeys(offers)],
        obj.version,
    )


def _character_offers(
    game_maps: GameMaps, pret_map: PretMap, obj: MapObject, curation: CharacterCuration
) -> list[NpcOffer]:
    """Dons, ventes, échanges et services du personnage (aucun pour la 2e génération, cf. en-tête du module)."""
    match game_maps.repo:
        case PretRepo() as repo:
            return _gen1_character_offers(game_maps.game, repo, pret_map, obj, curation)
        case Gen2PretRepo():
            return []


def _gen1_character_offers(
    game: Game, repo: PretRepo, pret_map: PretMap, obj: MapObject, curation: CharacterCuration
) -> list[NpcOffer]:
    """Offres lues dans le texte du personnage et relues à la main dans npc_offers.csv."""
    trainer_class = obj.trainer_class and obj.trainer_class.removeprefix("OPP_")
    offers = repo.npc_offers(obj.text) + character_services(repo, obj.text)
    if trainer_class in GYM_LEADERS:
        offers += [offer for offer in repo.leader_gifts(pret_map.label) if offer not in offers]
    curated = curation.offers_for(game.pret_repo, obj.text)
    exchanged = {offer.item for offer in curated if offer.kind == "exchange"}
    return [offer for offer in offers if not (offer.kind == "gift_item" and offer.item in exchanged)] + curated


def _facility_rows(game_maps: GameMaps, pret_map: PretMap) -> list[ObjectRow]:
    """Installations de la carte (aucune pour la 2e génération, cf. en-tête du module)."""
    match game_maps.repo:
        case PretRepo() as repo:
            return _gen1_facility_rows(game_maps.game, game_maps, repo, pret_map)
        case Gen2PretRepo():
            return []


def _gen1_facility_rows(game: Game, game_maps: GameMaps, repo: PretRepo, pret_map: PretMap) -> list[ObjectRow]:
    """Distributeurs et comptoirs des lots de la carte : une seule installation par service identique
    (les trois distributeurs côte à côte du toit du Centre Commercial vendent les mêmes boissons)."""
    prize_signs = [sign for sign in pret_map.signs if facility_kind(repo, sign.text) == PRIZE_VENDOR]
    rows: list[ObjectRow] = []
    for sign in pret_map.signs:
        kind = facility_kind(repo, sign.text)
        if kind is None:
            continue
        offers = _facility_offers(game, repo, kind, sign, prize_signs)
        if any(row.kind == kind and row.offers == offers for row in rows):
            continue
        x, y = game_maps.point(pret_map.const, sign.x, sign.y)
        rows.append(ObjectRow(pret_map.const, kind, x, y, None, None, None, None, None, offers=offers))
    return rows


def _facility_offers(game: Game, repo: PretRepo, kind: str, sign: Sign, prize_signs: list[Sign]) -> list[NpcOffer]:
    if kind == VENDING_MACHINE:
        offers = vending_offers(repo)
    elif kind == PRIZE_VENDOR:
        # Le comptoir est choisi d'après le rang de son texte (TEXT_…_PRIZE_VENDOR_1 à 3) : PrizeDifferentMenuPtrs.
        window = sorted(prize.text for prize in prize_signs).index(sign.text)
        offers = prize_offers(repo, window, game.pret_versions)
    else:
        raise ValueError(f"Installation inconnue : {kind}")
    return [_offer_identifiers(repo.machines, offer) for offer in offers]


def _offer_identifiers(machines: dict[str, str], offer: NpcOffer) -> NpcOffer:
    """Offre avec les identifiants PokéAPI à la place des constantes pret."""
    return NpcOffer(
        offer.kind,
        offer.item and item_identifier(offer.item, machines),
        offer.pokemon and species_identifier(offer.pokemon),
        offer.quantity,
        offer.price,
        offer.wanted and species_identifier(offer.wanted),
        offer.wanted_item and item_identifier(offer.wanted_item, machines),
        offer.version,
    )
