package org.opensources.pokmaps.domain.model

/**
 * Carte affichable d'un jeu (carte du monde ou carte intérieure), découpée en tuiles dans les assets.
 * Les dimensions sont en pixels Game Boy, à la taille réelle du jeu (dernier niveau de zoom).
 */
data class GameMap(
    val id: Int,
    val identifier: String,
    val name: String,
    val versionGroupIdentifier: String,
    val width: Int,
    val height: Int,
    val levelCount: Int,
    /** Villes et routes, pour la carte du monde. */
    val regions: List<MapRegion> = emptyList()
) {
    /** Chemin d'une tuile dans les assets (niveau 0 = carte entière dans une seule tuile). */
    fun tilePath(level: Int, row: Int, column: Int): String =
        "maps/$versionGroupIdentifier/$identifier/$level/${row}_$column.webp"

    companion object {
        const val TILE_SIZE = 256
        const val WORLD = "kanto"
    }
}

/** Partie d'une carte affichable (ville ou route de la carte du monde), en pixels. */
data class MapRegion(
    val id: Int,
    val identifier: String,
    val name: String,
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int
) {
    val centerX: Int get() = x + width / 2
    val centerY: Int get() = y + height / 2

    fun contains(px: Int, py: Int): Boolean = px in x until x + width && py in y until y + height
}
