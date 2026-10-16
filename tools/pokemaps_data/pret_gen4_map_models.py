"""Données de lieux DS communes à Platine et à Diamant/Perle : en-têtes, matrices, événements, zones, éclairages.

Les valeurs sont celles du moteur (entiers des fichiers compilés). Platine les écrit par leur nom dans ses JSON
et en-têtes : son lecteur les convertit avec les énumérations du dépôt, comme le fait sa construction, si bien
que les deux dépôts se comparent valeur à valeur.
"""

from __future__ import annotations

from dataclasses import dataclass

# Une matrice compte au plus 255 blocs de côté (u8 dans le format compilé).
MAX_MATRIX_SIDE = 255
# Numéro de bloc des cases vides d'une matrice (MAP_NONE).
EMPTY_BLOCK = 0xFFFF
# Valeur de champ « sans table de rencontres » des en-têtes (ENCOUNTERS_NONE).
NO_ENCOUNTERS = 0xFFFF
# Types de lieux (enum MapType de Platine, mêmes valeurs dans map_header.c de Diamant/Perle).
MAP_TYPES = ("none", "town", "outdoors", "cave", "indoors", "pokecenter", "underground")


@dataclass(frozen=True)
class Gen4Header:
    """En-tête de lieu (MapHeader) : indice dans la table du moteur et fichiers qu'il désigne."""

    index: int
    constant: str
    area: int
    move_models: int
    matrix: int
    scripts: int
    init_scripts: int
    texts: int
    day_music: str
    night_music: str
    # (version, numéro de table) pour chaque version ; vide si le lieu n'a pas de rencontres.
    encounters: tuple[tuple[str, int], ...]
    events: int
    location: str
    weather: int
    camera: int
    map_type: int
    battle_background: int
    bike: bool
    running: bool
    escape_rope: bool
    fly: bool

    def __post_init__(self) -> None:
        if not 0 <= self.map_type < len(MAP_TYPES):
            raise ValueError(f"{self.constant} : type de lieu inconnu : {self.map_type}")
        if any(table == NO_ENCOUNTERS for _, table in self.encounters):
            raise ValueError(f"{self.constant} : table de rencontres vide déclarée")


@dataclass(frozen=True)
class Gen4Matrix:
    """Matrice de blocs : `blocks[ligne][colonne]` (EMPTY_BLOCK si vide), en-têtes et altitudes facultatifs."""

    index: int
    name: str
    blocks: tuple[tuple[int, ...], ...]
    headers: tuple[tuple[int, ...], ...] | None
    altitudes: tuple[tuple[int, ...], ...] | None

    @property
    def width(self) -> int:
        return len(self.blocks[0])

    @property
    def height(self) -> int:
        return len(self.blocks)

    def __post_init__(self) -> None:
        height = len(self.blocks)
        if not 0 < height <= MAX_MATRIX_SIDE or not 0 < len(self.blocks[0]) <= MAX_MATRIX_SIDE:
            raise ValueError(f"matrice {self.index} : dimensions invalides")
        for grid in (self.blocks, self.headers, self.altitudes):
            if grid is not None and (len(grid) != height or {len(row) for row in grid} != {self.width}):
                raise ValueError(f"matrice {self.index} : grilles de tailles différentes")


@dataclass(frozen=True)
class ObjectEvent:
    """Personnage, objet ou Pokémon posé (ObjectEvent) ; coordonnées globales en cases."""

    local_id: int
    graphics: int
    movement: int
    trainer_type: int
    hidden_flag: int
    script: int
    direction: int
    data: tuple[int, int, int]
    range_x: int
    range_z: int
    x: int
    z: int
    # Hauteur en unités fx32 (1 case = 16 × 4096).
    y: int


@dataclass(frozen=True)
class WarpEvent:
    x: int
    z: int
    destination_header: int
    destination_warp: int


@dataclass(frozen=True)
class CoordEvent:
    """Déclencheur au sol : script exécuté quand la variable `var` vaut `value`."""

    script: int
    x: int
    z: int
    width: int
    length: int
    y: int
    value: int
    var: int


@dataclass(frozen=True)
class BgEvent:
    """Panneau, objet caché ou case interactive (BgEvent)."""

    script: int
    kind: int
    x: int
    z: int
    y: int
    facing: int


@dataclass(frozen=True)
class Gen4Events:
    index: int
    bg_events: tuple[BgEvent, ...]
    object_events: tuple[ObjectEvent, ...]
    warp_events: tuple[WarpEvent, ...]
    coord_events: tuple[CoordEvent, ...]


@dataclass(frozen=True)
class Gen4Area:
    """Zone (area_data) : jeu d'objets posés, jeu de textures du terrain, éclairage."""

    index: int
    prop_set: int
    texture_set: int
    # Champ « dummy » des sources, que le moteur ne lit pas ; conservé pour comparer les deux dépôts.
    dummy: int
    lighting: int


@dataclass(frozen=True)
class Light:
    enabled: bool
    color: tuple[int, int, int]
    # Direction en fx16 (4096 = 1,0).
    direction: tuple[int, int, int]


@dataclass(frozen=True)
class LightingPeriod:
    """Éclairage valable jusqu'à `end_time`, compté en pas de deux secondes depuis minuit (43 200 au plus)."""

    end_time: int
    lights: tuple[Light, Light, Light, Light]
    diffuse: tuple[int, int, int]
    ambient: tuple[int, int, int]
    specular: tuple[int, int, int]
    emission: tuple[int, int, int]


@dataclass(frozen=True)
class CameraSettings:
    """Réglages d'un type de caméra du terrain ; angle en indice de cercle (65 536 = 360°)."""

    distance: int
    angle_x: int
    projection: int
    vertical_fov: int
    near: int
    far: int
