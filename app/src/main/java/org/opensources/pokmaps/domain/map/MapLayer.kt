package org.opensources.pokmaps.domain.map

/**
 * Filtres de la carte : chaque calque montre ou cache une catégorie de marqueurs, dans le lieu sélectionné comme
 * ailleurs sur la carte (en dehors du lieu sélectionné, les marqueurs n'apparaissent qu'en zoomant).
 */
enum class MapLayer {
    WARPS,
    ITEMS,
    TRAINERS,
    NPCS,
    STATIC_POKEMON,
    WILD_POKEMON;

    companion object {
        /** Calque d'un objet ou d'un personnage de la carte. */
        fun of(kind: MapObjectKind): MapLayer = when (kind) {
            MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> ITEMS

            MapObjectKind.TRAINER -> TRAINERS

            MapObjectKind.POKEMON -> STATIC_POKEMON

            MapObjectKind.NPC, MapObjectKind.NPC_OBJECT, MapObjectKind.NPC_POKEMON, MapObjectKind.VENDING_MACHINE,
            MapObjectKind.PRIZE_VENDOR, MapObjectKind.HEAL_SPOT -> NPCS
        }
    }
}
