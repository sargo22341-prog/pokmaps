"""Modeles des donnees extraites des depots pret."""

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
    text: str | None = None  # constante du texte affiché quand on parle au personnage (ex. TEXT_ROUTE1_YOUNGSTER1)


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
    signs: list[tuple[int, int]] = field(default_factory=list)
    objects: list[MapObject] = field(default_factory=list)

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


@dataclass(frozen=True)
class NpcOffer:
    """Ce que propose un personnage quand on lui parle (d'après le script de son texte)."""

    kind: str  # gift_item, gift_pokemon, sale ou trade
    item: str | None = None  # constante d'objet (gift_item, sale)
    pokemon: str | None = None  # Pokémon donné (gift_pokemon) ou reçu lors d'un échange (trade)
    quantity: int | None = None  # nombre d'objets donnés, ou niveau du Pokémon donné
    price: int | None = None  # prix en magasin (sale)
    wanted: str | None = None  # Pokémon demandé en échange (trade)


