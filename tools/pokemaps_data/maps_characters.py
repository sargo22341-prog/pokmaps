"""Personnages, dresseurs, objets et installations des cartes, avec ce qu'ils proposent.

Les objets de carte viennent des object_event pret (personnages, dresseurs, objets, Pokémon fixes) et des
bg_event qui rendent un service (distributeur, comptoir des lots, lit) ; leurs offres viennent des scripts pret
(1re génération : `pret.py`, `pret_services.py` ; 2e : `pret_gen2_offers.py`) et, quand le script ne se lit pas
simplement, de tools/data/npc_offers.csv (maps_characters_data).

Un même personnage apparaît parfois plusieurs fois dans pret, un exemplaire par étape du scénario (le
Prof. Chen qui vient chercher le joueur, puis dans son labo) : tools/data/npc_duplicates.csv écarte ces
doublons pour qu'il n'en reste qu'un, celui avec qui l'on interagit vraiment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .games import Game
from .maps_characters_data import CharacterCuration, character_key
from .maps_layout import GameMaps, identifier
from .offer_conditions import Condition
from .pret import GYM_LEADERS, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_gen2_offers import SERVICE_KINDS
from .pret_identifiers import item_identifier, species_identifier
from .pret_models import HIDDEN_ITEM, MapObject, NpcOffer, PretMap, Sign
from .pret_services import (
    HEAL_SPOT,
    PRIZE_VENDOR,
    VENDING_MACHINE,
    character_services,
    facility_kind,
    prize_offers,
    vending_offers,
)

# Classes de dresseurs dont l'équipe dépend du starter choisi (fixée par le script, pas par la carte).
STARTER_DEPENDENT_TRAINERS = frozenset({"RIVAL1", "RIVAL2", "RIVAL3"})
# Objets à ramasser : leur « script » est l'objet lui-même (itemball, hiddenitem), sans offre.
_PICKED_UP = frozenset({"item", HIDDEN_ITEM})


@dataclass
class ObjectRow:
    map_const: str
    kind: str  # npc, item, hidden_item, trainer, pokemon, vending_machine, prize_vendor ou heal_spot
    x: int
    y: int
    sprite: str | None
    item: str | None  # identifiant PokéAPI
    pokemon: str | None  # identifiant PokéAPI
    level: int | None
    trainer_class: str | None
    # Ce qui désigne le personnage ou l'installation dans tools/data/ (maps_characters_data.character_key ; label du
    # script pour une installation de la 2e génération).
    key: str | None = None
    # Équipe d'un dresseur : (Pokémon, niveau, attaques), identifiants PokéAPI.
    party: list[tuple[str, int, tuple[str, ...]]] = field(default_factory=list)
    # Dons, ventes, échanges et services (identifiants PokéAPI).
    offers: list[NpcOffer] = field(default_factory=list)
    # Version PokéAPI où l'objet est ainsi (Ho-Oh et Lugia n'ont pas le même niveau en Or et en Argent), None s'il
    # est le même dans toutes les versions du jeu.
    version: str | None = None
    # Pokémon dont le personnage pousse le cri (identifiant PokéAPI) : il nomme un personnage à l'apparence d'un
    # Pokémon (2e génération).
    cry: str | None = None


def object_rows(game_maps: GameMaps, curation: CharacterCuration) -> tuple[list[ObjectRow], set[str]]:
    """Objets de toutes les cartes placées du jeu, et sprites de personnages à exporter."""
    objects: list[ObjectRow] = []
    sprites: set[str] = set()
    for const in sorted(game_maps.placements, key=lambda c: game_maps.maps[c].number):
        pret_map = game_maps.maps[const]
        for position, obj in enumerate(pret_map.objects):
            if not (0 <= obj.x < pret_map.width * 2 and 0 <= obj.y < pret_map.height * 2):
                continue  # hors de la carte, donc inaccessible (ex. une Pépite cachée de l'entrée du Parc Safari)
            if curation.is_duplicate(character_key(obj)):
                continue
            if obj.sprite:
                sprites.add(obj.sprite)
            objects.append(_character_row(game_maps, pret_map, position, obj, curation))
        objects += _facility_rows(game_maps, pret_map)
    return objects, sprites


def _character_row(
    game_maps: GameMaps, pret_map: PretMap, position: int, obj: MapObject, curation: CharacterCuration
) -> ObjectRow:
    repo = game_maps.repo
    trainer_class = obj.trainer_class and obj.trainer_class.removeprefix("OPP_")
    party = []
    if trainer_class and trainer_class not in STARTER_DEPENDENT_TRAINERS:
        party = [
            (species_identifier(mon.species), mon.level, tuple(identifier(move) for move in mon.moves))
            for mon in repo.trainer_parties.get((trainer_class, obj.trainer_number or 0), [])
        ]
    offers = _character_offers(game_maps, pret_map, position, obj, curation)
    return ObjectRow(
        pret_map.const,
        obj.kind,
        *game_maps.point(pret_map.const, obj.x, obj.y),
        obj.sprite and identifier(obj.sprite.removeprefix("SPRITE_")),
        obj.item and item_identifier(obj.item, repo.machines),
        obj.pokemon and species_identifier(obj.pokemon),
        obj.level,
        trainer_class and identifier(trainer_class),
        character_key(obj),
        party,
        [_offer_identifiers(repo.machines, offer) for offer in dict.fromkeys(offers)],
        obj.version,
        obj.cry and species_identifier(obj.cry),
    )


def _character_offers(
    game_maps: GameMaps, pret_map: PretMap, position: int, obj: MapObject, curation: CharacterCuration
) -> list[NpcOffer]:
    """Dons, ventes, échanges et services du personnage (`position` : rang de son object_event dans la carte)."""
    match game_maps.repo:
        case PretRepo() as repo:
            return _gen1_character_offers(game_maps.game, repo, pret_map, position, obj, curation)
        case Gen2PretRepo() as repo:
            return _gen2_character_offers(game_maps.game, repo, pret_map, obj, curation)


def _gen1_character_offers(
    game: Game, repo: PretRepo, pret_map: PretMap, position: int, obj: MapObject, curation: CharacterCuration
) -> list[NpcOffer]:
    """Offres lues dans le texte du personnage et relues à la main dans npc_offers.csv, avec ce qu'exige sa
    présence (pret_conditions)."""
    trainer_class = obj.trainer_class and obj.trainer_class.removeprefix("OPP_")
    offers = repo.npc_offers(obj.text) + character_services(repo, obj.text)
    if trainer_class in GYM_LEADERS:
        offers += [offer for offer in repo.leader_gifts(pret_map.label) if offer not in offers]
    presence = repo.conditions.presence(pret_map.label, position, repo.conditions.offer_place(obj.text))
    offers = _with_curated(offers, curation.offers_for(game.pret_repo, character_key(obj)))
    return _present(offers, presence)


def _gen2_character_offers(
    game: Game, repo: Gen2PretRepo, pret_map: PretMap, obj: MapObject, curation: CharacterCuration
) -> list[NpcOffer]:
    """Offres lues dans le script du personnage, corrigées par npc_offers.csv, avec ce qu'exige sa présence.

    Un dresseur ne rend pas de service : les soins qui suivent son combat remettent l'équipe en état pour la suite
    de la scène (le marin paresseux du M/S Aquaria, Red au sommet du Mont Argenté)."""
    key = character_key(obj)
    added = curation.offers_for(game.pret_repo, key)
    script_file = repo.script_files[pret_map.label]
    if obj.kind in _PICKED_UP or obj.text is None or not script_file.has_label(obj.text):
        return _present(added, repo.presence.condition(pret_map, obj, frozenset()))
    read = repo.offers.script_offers(script_file, obj.text)
    if read.curated_specials and not added:
        specials = sorted(read.curated_specials)
        raise ValueError(f"npc_offers.csv : offre de {key} ({pret_map.const}) à relire, faite par {specials}")
    offers = [offer for offer in read.offers if not (obj.kind == "trainer" and offer.kind in SERVICE_KINDS)]
    offers = _with_curated(curation.without_removed(game.pret_repo, key, offers), added)
    return _present(offers, repo.presence.condition(pret_map, obj, read.points))


def _present(offers: list[NpcOffer], presence: Condition) -> list[NpcOffer]:
    """Offres du personnage, chacune exigeant aussi ce qu'exige sa présence."""
    return [replace(offer, condition=offer.condition.meet(presence)) for offer in offers]


def _with_curated(offers: list[NpcOffer], curated: list[NpcOffer]) -> list[NpcOffer]:
    """Offres lues et offres ajoutées à la main : un échange remplace le don du même objet lu dans le script."""
    exchanged = {offer.item for offer in curated if offer.kind == "exchange"}
    return [offer for offer in offers if not (offer.kind == "gift_item" and offer.item in exchanged)] + curated


def _facility_rows(game_maps: GameMaps, pret_map: PretMap) -> list[ObjectRow]:
    """Installations de la carte : une seule par service identique (les distributeurs côte à côte du toit du
    Centre Commercial vendent les mêmes boissons)."""
    match game_maps.repo:
        case PretRepo() as repo:
            rows = _gen1_facility_rows(game_maps.game, game_maps, repo, pret_map)
        case Gen2PretRepo() as repo:
            rows = _gen2_facility_rows(game_maps, repo, pret_map)
    unique: list[ObjectRow] = []
    for row in rows:
        if not any(
            other.kind == row.kind and other.offers == row.offers and other.item == row.item for other in unique
        ):
            unique.append(row)
    return unique


def _gen1_facility_rows(game: Game, game_maps: GameMaps, repo: PretRepo, pret_map: PretMap) -> list[ObjectRow]:
    """Distributeurs et comptoirs des lots de la carte."""
    prize_signs = [sign for sign in pret_map.signs if facility_kind(repo, sign.text) == PRIZE_VENDOR]
    rows: list[ObjectRow] = []
    for sign in pret_map.signs:
        kind = facility_kind(repo, sign.text)
        if kind is None:
            continue
        offers = _facility_offers(game, repo, kind, sign, prize_signs)
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


def _gen2_facility_rows(game_maps: GameMaps, repo: Gen2PretRepo, pret_map: PretMap) -> list[ObjectRow]:
    """Panneaux dont le script rend un service : distributeurs, comptoirs des lots, lits et machines de soins. Une
    poubelle qui donne un objet une seule fois (les Restes du Café de Céladopole) est un objet caché."""
    script_file = repo.script_files[pret_map.label]
    rows: list[ObjectRow] = []
    for sign in pret_map.signs:
        if not script_file.has_label(sign.text):
            continue
        read = repo.offers.script_offers(script_file, sign.text)
        if read.curated_specials:
            raise ValueError(f"{pret_map.const} : installation {sign.text} à relire ({sorted(read.curated_specials)})")
        kind = _gen2_facility_kind(pret_map, sign, list(read.offers))
        if kind is None:
            continue
        x, y = game_maps.point(pret_map.const, sign.x, sign.y)
        offers = [_offer_identifiers(repo.machines, offer) for offer in read.offers]
        if kind == HIDDEN_ITEM:
            rows.append(ObjectRow(pret_map.const, kind, x, y, None, offers[0].item, None, None, None, sign.text))
        else:
            rows.append(ObjectRow(pret_map.const, kind, x, y, None, None, None, None, None, sign.text, offers=offers))
    return rows


def _gen2_facility_kind(pret_map: PretMap, sign: Sign, offers: list[NpcOffer]) -> str | None:
    """Type d'installation d'après ce que propose son script, None pour un simple panneau."""
    kinds = {offer.kind for offer in offers}
    if not kinds:
        return None
    if kinds == {"sale"}:
        return VENDING_MACHINE
    if kinds <= {"prize_item", "prize_pokemon"}:
        return PRIZE_VENDOR
    if kinds == {"heal"}:
        return HEAL_SPOT
    if kinds == {"gift_item"} and len(offers) == 1 and offers[0].quantity == 1:
        return HIDDEN_ITEM
    raise ValueError(f"{pret_map.const} : installation {sign.text} non prise en charge : {sorted(kinds)}")


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
        offer.condition,
    )
