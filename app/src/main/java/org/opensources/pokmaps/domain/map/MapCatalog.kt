package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.MapRegion

/** Carte d'un jeu : affichable (carte du monde ou intérieure) ou partie de la carte du monde (ville, route). */
data class MapInfo(
    val id: Int,
    val identifier: String,
    val name: String,
    val parentId: Int?,
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
    val levelCount: Int
) {
    val isDisplayable: Boolean get() = parentId == null && levelCount > 0

    fun toRegion() = MapRegion(id, identifier, name, x, y, width, height)
}

/** Porte, escalier ou entrée de grotte, en pixels de la carte affichée ; arrivée inconnue si `targetMapId` est null. */
data class MapWarp(
    val id: Int,
    val mapId: Int,
    val x: Int,
    val y: Int,
    val targetMapId: Int?,
    val targetX: Int?,
    val targetY: Int?
)

enum class MapObjectKind(val identifier: String) {
    ITEM("item"),
    HIDDEN_ITEM("hidden_item"),
    TRAINER("trainer"),
    POKEMON("pokemon"),
    NPC("npc");

    companion object {
        fun from(identifier: String): MapObjectKind = entries.firstOrNull { it.identifier == identifier } ?: NPC
    }
}

/** Objet, dresseur, Pokémon fixe ou PNJ d'une carte (centre de sa case, en pixels de la carte affichée). */
data class MapObject(
    val id: Int,
    val mapId: Int,
    val kind: MapObjectKind,
    val x: Int,
    val y: Int,
    val sprite: String?,
    val itemId: Int?,
    val itemIdentifier: String?,
    val itemName: String?,
    val pokemonId: Int?,
    val pokemonName: String?,
    val level: Int?,
    val trainerClass: String?
)

/** Zone de rencontre PokéAPI rattachée à une carte. */
data class MapArea(val mapId: Int, val areaId: Int, val name: String)

/** Toutes les cartes d'un jeu, avec leurs warps, objets et zones de rencontre. */
data class MapCatalog(
    val versionGroupIdentifier: String,
    val maps: Map<Int, MapInfo>,
    val warps: Map<Int, List<MapWarp>>,
    val objects: Map<Int, List<MapObject>>,
    val areas: Map<Int, List<MapArea>>,
    /** Emplacements des Pokémon sauvages de chaque carte (ville, route ou carte intérieure). */
    val spots: Map<Int, List<MapSpot>> = emptyMap()
) {
    val world: MapInfo? = maps.values.firstOrNull { it.identifier == GameMap.WORLD && it.isDisplayable }

    /** Carte affichable qui contient `mapId` : elle-même, ou la carte du monde pour une ville ou une route. */
    fun displayedMapOf(mapId: Int): MapInfo? {
        val map = maps[mapId] ?: return null
        return if (map.parentId == null) map else maps[map.parentId]
    }

    /** Villes et routes d'une carte affichable (vide pour une carte intérieure). */
    fun regionsOf(mapId: Int): List<MapInfo> = maps.values.filter { it.parentId == mapId }.sortedBy { it.id }

    /** Cartes (elle-même et ses villes ou routes) dont les objets et warps se dessinent sur la carte affichable. */
    fun partsOf(mapId: Int): List<Int> = listOf(mapId) + regionsOf(mapId).map { it.id }

    fun gameMap(mapId: Int): GameMap? {
        val map = maps[mapId]?.takeIf { it.isDisplayable } ?: return null
        return GameMap(
            id = map.id,
            identifier = map.identifier,
            name = map.name,
            versionGroupIdentifier = versionGroupIdentifier,
            width = map.width,
            height = map.height,
            levelCount = map.levelCount,
            regions = regionsOf(map.id).map { it.toRegion() }
        )
    }

    /**
     * Warps d'une carte affichable à dessiner : un seul par destination et par entrée
     * (les portes larges ont plusieurs cases qui mènent au même endroit).
     */
    fun entrancesOf(mapId: Int): List<MapWarp> {
        val kept = mutableListOf<MapWarp>()
        for (warp in partsOf(mapId).flatMap { warps[it].orEmpty() }) {
            val target = warp.targetMapId ?: continue
            if (displayedMapOf(target)?.id == mapId && maps[target]?.parentId != null) continue
            val duplicate = kept.any {
                it.targetMapId == target && abs(it.x - warp.x) <= MERGE_DISTANCE &&
                    abs(it.y - warp.y) <= MERGE_DISTANCE
            }
            if (!duplicate) kept += warp
        }
        return kept
    }

    /**
     * Warps vers les lieux accessibles depuis une ville, une route ou une carte intérieure (bâtiments, grottes,
     * étages, sorties), un par lieu. Depuis une ville ou une route, seules les cartes intérieures comptent.
     */
    fun accessibleFrom(mapId: Int): List<MapWarp> {
        val zone = maps[mapId] ?: return emptyList()
        val candidates = if (zone.parentId == null) entrancesOf(zone.id) else warps[zone.id].orEmpty()
        return candidates.filter { warp ->
            val target = warp.targetMapId?.let { maps[it] } ?: return@filter false
            target.id != zone.id && (zone.parentId == null || target.parentId == null)
        }.distinctBy { it.targetMapId }
    }

    /** Tous les objets et personnages du jeu, par identifiant. */
    val objectsById: Map<Int, MapObject> by lazy { objects.values.flatten().associateBy { it.id } }

    /** Carte (affichable ou ville, route) d'après son identifiant. */
    fun mapByIdentifier(identifier: String): MapInfo? = maps.values.firstOrNull { it.identifier == identifier }

    /**
     * Entrée sur la carte du monde de chaque carte intérieure : le warp de la carte du monde par lequel
     * on l'atteint en passant par le moins de cartes (Mont Sélénite sous-sol 2 → entrée du Mont Sélénite).
     */
    fun worldEntrances(): Map<Int, MapWarp> {
        val world = world ?: return emptyMap()
        val result = mutableMapOf<Int, MapWarp>()
        val queue = ArrayDeque<Pair<Int, MapWarp>>()
        for (warp in partsOf(world.id).flatMap { warps[it].orEmpty() }) {
            val target = warp.targetMapId ?: continue
            if (maps[target]?.isDisplayable == true && target != world.id && target !in result) {
                result[target] = warp
                queue += target to warp
            }
        }
        while (queue.isNotEmpty()) {
            val (mapId, entrance) = queue.removeFirst()
            for (warp in warps[mapId].orEmpty()) {
                val target = warp.targetMapId ?: continue
                if (maps[target]?.isDisplayable == true && target != world.id && target !in result) {
                    result[target] = entrance
                    queue += target to entrance
                }
            }
        }
        return result
    }

    /** Bâtiments et grottes à plusieurs niveaux (cartes affichables), étages rangés de haut en bas. */
    private val buildings: Map<String, List<MapFloor>> by lazy {
        maps.values.filter { it.isDisplayable }
            .mapNotNull { map ->
                FloorLevel.parse(map.identifier)?.let { (building, level) -> building to MapFloor(map.id, level) }
            }
            .groupBy({ it.first }, { it.second })
            .filterValues { it.size > 1 }
            .mapValues { (_, floors) -> floors.sortedByDescending { it.level.order } }
    }

    private val buildingOf: Map<Int, String> by lazy {
        buildings.flatMap { (building, floors) -> floors.map { it.mapId to building } }.toMap()
    }

    /** Étages du bâtiment ou de la grotte d'une carte intérieure (vide si elle n'a qu'un niveau). */
    fun floorsOf(mapId: Int): List<MapFloor> = buildingOf[mapId]?.let { buildings[it] }.orEmpty()

    /** Pour chaque carte intérieure, le warp par lequel on l'atteint en premier en partant de l'extérieur. */
    private val reachedBy: Map<Int, MapWarp> by lazy {
        val world = world ?: return@lazy emptyMap()
        val result = mutableMapOf<Int, MapWarp>()
        val queue = ArrayDeque(partsOf(world.id))
        while (queue.isNotEmpty()) {
            for (warp in warps[queue.removeFirst()].orEmpty()) {
                val target = warp.targetMapId ?: continue
                if (maps[target]?.isDisplayable == true && target != world.id && target !in result) {
                    result[target] = warp
                    queue += target
                }
            }
        }
        result
    }

    /**
     * Entrée d'une carte intérieure dans le niveau du dessus : le warp (sur la ville, la route ou la carte
     * intérieure parente) qui y mène. Les étages d'un même bâtiment ont tous l'entrée du bâtiment : depuis le
     * 2e sous-sol du Mont Sélénite, on remonte directement à l'entrée du Mont Sélénite sur la Route 3.
     */
    fun parentEntrance(mapId: Int): MapWarp? {
        val building = buildingOf[mapId]
        var warp = reachedBy[mapId] ?: return null
        val seen = mutableSetOf(mapId)
        while (building != null && buildingOf[warp.mapId] == building && seen.add(warp.mapId)) {
            warp = reachedBy[warp.mapId] ?: return null
        }
        return warp
    }

    private companion object {
        const val MERGE_DISTANCE = 32
    }
}
