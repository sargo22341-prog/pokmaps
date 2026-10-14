package org.opensources.pokmaps.domain.model

/**
 * Carte affichable d'un jeu (carte du monde d'une région ou lieu à part), découpée en tuiles dans les assets.
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
    /** Villes et routes de la carte du monde, ou zones et salles d'un niveau composé. */
    val regions: List<MapRegion> = emptyList(),
    val isWorld: Boolean = false,
    val startRegionId: Int? = null,
    /** Version du jeu affiché (ruby) : choisit les retouches propres à cette version. */
    val versionIdentifier: String? = null
) {
    val isExternalEvent: Boolean get() = ExternalEvent.map(identifier)

    /** Chemin d'une tuile dans les assets (niveau 0 = carte entière dans une seule tuile). */
    fun tilePath(level: Int, row: Int, column: Int): String =
        "maps/$versionGroupIdentifier/$identifier/$level/${row}_$column.webp"

    /**
     * Mer répétée sous la carte des Îles Sevii, la même tuile pour tout un niveau de zoom : elle prolonge l'eau
     * des routes sans limite visible avec le fond. Null pour les autres cartes.
     */
    fun seaTilePath(level: Int): String? =
        if (identifier == SEA_WORLD) "maps/$versionGroupIdentifier/$SEA_WORLD-water/$level.webp" else null

    /**
     * Tuile des cases que seule la version affichée retouche, dessinées par-dessus la carte commune au groupe :
     * dans Rubis, Nénucrique ouvre l'entrée de la Planque Magma une case à droite de celle de Saphir. Le pipeline
     * écrit ces tuiles dans le même dossier (maps_gen3.version_patch_folder). Null pour les autres cartes.
     */
    fun versionTilePath(level: Int, row: Int, column: Int): String? {
        val folder = "$identifier-$versionIdentifier"
        if (folder !in VERSION_PATCHES) return null
        return "maps/$versionGroupIdentifier/$folder/$level/${row}_$column.webp"
    }

    companion object {
        const val TILE_SIZE = 256
        private const val SEA_WORLD = "sevii"
        private val VERSION_PATCHES = setOf("hoenn-ruby")
    }
}

/** Partie d'une carte affichable (ville, route, zone ou salle), en pixels. */
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
