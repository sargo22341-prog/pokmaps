"""Modèles des données extraites des dépôts pret."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Connection:
    direction: str  # north, south, west, east
    target: str  # constante de la carte voisine (ex. ROUTE_1)
    offset: int  # décalage de la carte voisine, en blocs (x pour nord/sud, y pour ouest/est)


@dataclass(frozen=True)
class Warp:
    x: int
    y: int
    target: str  # constante de la carte d'arrivée, ou LAST_MAP (la carte d'où l'on vient)
    target_warp: int  # numéro du warp d'arrivée, à partir de 1
    # Faux si pret le signale inaccessible (« ; inaccessible ») : on ne peut pas s'y tenir dans le jeu.
    accessible: bool = True


@dataclass(frozen=True)
class Sign:
    """Panneau, distributeur ou comptoir (bg_event) : le joueur le lit en se tenant devant."""

    x: int
    y: int
    text: str  # constante du texte affiché (ex. TEXT_CELADONMARTROOF_VENDING_MACHINE1)


@dataclass(frozen=True)
class MapObject:
    x: int
    y: int
    kind: str  # npc, item, hidden_item, trainer, pokemon
    sprite: str | None = None  # ex. SPRITE_YOUNGSTER
    item: str | None = None  # ex. MOON_STONE, TM_MEGA_PUNCH
    pokemon: str | None = None  # ex. ZAPDOS
    level: int | None = None
    trainer_class: str | None = None  # ex. OPP_YOUNGSTER
    trainer_number: int | None = None  # numéro de l'équipe dans la classe (data/trainers/parties.asm)
    # Ce qui identifie le personnage dans pret : la constante du texte affiché quand on lui parle en 1re génération
    # (ex. TEXT_ROUTE1_YOUNGSTER1), le label de son script en 2e (ex. Route30YoungsterScript).
    text: str | None = None
    # Version PokéAPI où l'objet est ainsi (ex. gold), None s'il est le même dans toutes les versions du jeu.
    version: str | None = None
    # 2e génération : moments de la journée où l'objet est là (MORN, DAY, NITE), vide s'il est toujours là.
    times: frozenset[str] = frozenset()
    # 2e génération : drapeau d'événement qui cache l'objet une fois levé (ex. EVENT_ROUTE_30_BATTLE).
    event_flag: str | None = None


@dataclass
class PretMap:
    const: str
    number: int
    label: str
    width: int
    height: int
    tileset: str
    blocks: bytes
    border_block: int
    is_outdoor: bool
    connections: list[Connection] = field(default_factory=list)
    warps: list[Warp] = field(default_factory=list)
    signs: list[Sign] = field(default_factory=list)
    objects: list[MapObject] = field(default_factory=list)
    # Cartes où un script envoie le joueur sans warp de carte (commande warp de la 2e génération : inscription au
    # Concours de capture d'insectes, traversées du M/S Aquaria…).
    script_warps: list[str] = field(default_factory=list)

    def block(self, x: int, y: int) -> int:
        return self.blocks[y * self.width + x]


@dataclass(frozen=True)
class Tileset:
    const: str
    gfx: Path  # image des tuiles (16 tuiles de 8 px par ligne, niveaux de gris sur 2 bits)
    blockset: Path  # 16 octets par bloc : numéros des 4 × 4 tuiles
    grass_tile: int | None = None  # tuile des hautes herbes (rencontres en marchant), None si aucune
    passable: frozenset[int] = frozenset()  # tuiles où l'on peut marcher
    has_water: bool = False  # tileset avec de l'eau où surfer (tuile WATER_TILE)


# Tuile d'eau où l'on peut surfer (CollisionCheckOnWater dans home/overworld.asm).
WATER_TILE = 0x14


@dataclass(frozen=True)
class TrainerPokemon:
    species: str  # constante pret (ex. PIDGEY)
    level: int
    moves: tuple[str, ...]  # constantes des attaques (4 au plus)
    item: str | None = None  # objet tenu (2e génération), constante pret


@dataclass(frozen=True)
class NpcOffer:
    """Ce que propose un personnage quand on lui parle (d'après le script de son texte).

    kind : gift_item, gift_pokemon, sale, trade (Pokémon contre Pokémon), exchange (objet contre objet),
    prize_item et prize_pokemon (lots du Casino, prix en jetons), coin_sale (jetons vendus), coin_gift
    (jetons donnés), fossil (fossile ranimé), ou un service sans objet : heal, cable_club, name_rater, daycare.
    """

    kind: str
    item: str | None = None  # objet donné, vendu, gagné ou obtenu par échange ; fossile à ranimer
    pokemon: str | None = None  # Pokémon donné, gagné, reçu lors d'un échange ou ranimé
    quantity: int | None = None  # nombre d'objets ou de jetons, ou niveau du Pokémon donné, gagné ou ranimé
    price: int | None = None  # prix en ¥ (sale, coin_sale) ou en jetons (prize_item, prize_pokemon)
    wanted: str | None = None  # Pokémon demandé en échange (trade)
    wanted_item: str | None = None  # objet demandé en échange (exchange)
    version: str | None = None  # version PokéAPI où l'offre existe (ex. red), None pour toutes celles du jeu
