package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.MapRegion
import org.opensources.pokmaps.domain.model.VersionGroup

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
    val levelCount: Int,
    val isWorld: Boolean = false,
    val originMapId: Int? = null,
    val startMapId: Int? = null,
    val externalEventKey: String? = null,
    /** Ordre dans le menu des îles ; zéro pour les cartes qui ne sont pas une entrée. */
    val eventEntranceOrder: Int = 0
) {
    val isExternalEvent: Boolean get() = externalEventKey != null

    val isDisplayable: Boolean get() = parentId == null && levelCount > 0

    fun toRegion() = MapRegion(id, identifier, name, x, y, width, height)
}

/** Passage, en pixels de la carte affichée ; arrivée inconnue si `targetMapId` est null. */
data class MapWarp(
    val id: Int,
    val mapId: Int,
    val x: Int,
    val y: Int,
    val targetMapId: Int?,
    val targetX: Int?,
    val targetY: Int?,
    val kind: WarpKind = WarpKind.WARP
)

enum class MapObjectKind(val identifier: String) {
    ITEM("item"),
    HIDDEN_ITEM("hidden_item"),
    TRAINER("trainer"),
    POKEMON("pokemon"),

    /** Personnage : une personne. */
    NPC("npc"),

    /** Objet du décor qui parle ou donne quelque chose (Fossile, Poké Ball, rocher…). */
    NPC_OBJECT("npc_object"),

    /** Pokémon qui n'est pas à combattre (Otaria du Fan Club, Pokémon des maisons…). */
    NPC_POKEMON("npc_pokemon"),

    /** Distributeur de boissons (sans sprite : il fait partie du décor). */
    VENDING_MACHINE("vending_machine"),

    /** Comptoir des lots du Casino (sans sprite). */
    PRIZE_VENDOR("prize_vendor"),

    /** Lit ou machine qui soigne l'équipe (sans sprite : labo du Prof. Orme, cabines du M/S Aquaria). */
    HEAL_SPOT("heal_spot");

    companion object {
        fun from(identifier: String): MapObjectKind =
            requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
                "Type d'élément de carte inconnu : $identifier"
            }
    }
}

/** Objet, dresseur, Pokémon fixe, PNJ ou installation d'une carte (centre de sa case, en pixels de la carte). */
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
    val trainerClass: String?,
    /** Nom affiché : classe du dresseur, personnage d'après son sprite, Pokémon ou objet (tools/data/). */
    val name: String,
    val itemHasSprite: Boolean = true,
    val fruit: OfferItem? = null,
    val shiny: Boolean = false
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
    val spots: Map<Int, List<MapSpot>> = emptyMap(),
    /** Version du jeu, pour les dessins qui lui sont propres ; null dans les tests qui n'en dépendent pas. */
    val versionIdentifier: String? = null
) {
    // Index immuables calculés avec le catalogue, hors du fil principal (MapRepository), plutôt qu'à chaque
    // rendu de la carte. Déclarés avant les propriétés qui s'en servent pendant la construction.
    val battleMarkers: List<BattleMarkers.Position> = BattleMarkers.positions(objects.values.flatten())

    private val regionsByParent: Map<Int, List<MapInfo>> = maps.values
        .mapNotNull { map -> map.parentId?.let { it to map } }
        .groupBy({ it.first }, { it.second })
        .mapValues { (_, regions) -> regions.sortedBy { it.id } }

    /** Premier lieu de chaque identifiant, comme une recherche dans l'ordre des cartes. */
    private val byIdentifier: Map<String, MapInfo> = buildMap { maps.values.forEach { putIfAbsent(it.identifier, it) } }

    val worlds: List<MapInfo> = maps.values.filter { it.isDisplayable && isWorld(it.id) }.sortedBy { it.id }
    val regionWorlds: List<MapInfo> = MapDestinations.menu(worlds, maps.values)

    fun regionWorldOf(mapId: Int): MapInfo? = MapDestinations.eventOf(maps[mapId], regionWorlds)
        ?: worldOf(mapId)?.let { world ->
            if (world.identifier == "hoenn-underwater") mapByIdentifier("hoenn") else world
        }

    val defaultWorld: MapInfo? = worlds.firstOrNull {
        it.identifier == MapDestinations.startRegion(VersionGroup.of(versionGroupIdentifier))
    } ?: worlds.firstOrNull { it.identifier != "hoenn-underwater" }

    fun isWorld(mapId: Int): Boolean = maps[mapId]?.isWorld == true

    fun worldOf(mapId: Int): MapInfo? {
        val map = maps[mapId] ?: return null
        if (isWorld(map.id)) return map
        val display = displayedMapOf(mapId) ?: return null
        if (display.isWorld) return display
        val origin = maps[map.originMapId ?: display.originMapId]
        return maps[origin?.parentId]?.takeIf { isWorld(it.id) }
    }

    /** Carte affichable qui contient `mapId` : elle-même, ou la carte du monde pour une ville ou une route. */
    fun displayedMapOf(mapId: Int): MapInfo? {
        val map = maps[mapId] ?: return null
        return if (map.parentId == null) map else maps[map.parentId]
    }

    /** Villes et routes d'une carte affichable (vide pour une carte intérieure). */
    fun regionsOf(mapId: Int): List<MapInfo> = regionsByParent[mapId].orEmpty()

    /** Cartes (elle-même et ses villes ou routes) dont les objets et warps se dessinent sur la carte affichable. */
    fun partsOf(mapId: Int): List<Int> = listOf(mapId) + regionsOf(mapId).map { it.id }

    /** Les emplacements arbre de Sinnoh correspondent aux arbres à Miel, ceux de Johto à Coup d'Boule. */
    fun hasHoneyTrees(mapId: Int): Boolean =
        versionGroupIdentifier in setOf(VersionGroup.DIAMOND_PEARL.identifier, VersionGroup.PLATINUM.identifier) &&
            partsOf(mapId).any { id -> spots[id].orEmpty().any { it.kind == SpotKind.TREE } }

    fun connectionsOf(mapId: Int): List<MapConnection> = connections[mapId].orEmpty()

    private val connections: Map<Int, List<MapConnection>> = maps.values.filter { it.isDisplayable && !it.isWorld }
        .associate { it.id to MapConnections.build(this, it.id) }

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
            regions = regionsOf(map.id).map { it.toRegion() },
            isWorld = isWorld(map.id),
            startRegionId = map.startMapId,
            versionIdentifier = versionIdentifier,
            isExternalEvent = map.isExternalEvent
        )
    }

    /**
     * Warps d'une carte affichable à dessiner : un seul par destination et par entrée
     * (les portes larges ont plusieurs cases qui mènent au même endroit).
     */
    fun entrancesOf(mapId: Int): List<MapWarp> = entrances[mapId] ?: mergedEntrances(mapId)

    private val entrances: Map<Int, List<MapWarp>> =
        maps.values.filter { it.parentId == null }.associate { it.id to mergedEntrances(it.id) }

    private fun mergedEntrances(mapId: Int): List<MapWarp> {
        val kept = mutableListOf<MapWarp>()
        for (warp in partsOf(mapId).flatMap { warps[it].orEmpty() }) {
            if (warp.kind == WarpKind.SECRET_BASE) continue
            val target = warp.targetMapId ?: continue
            if (isWorld(mapId) && displayedMapOf(target)?.id == mapId) continue
            val duplicate = kept.any {
                it.targetMapId == target && abs(it.x - warp.x) <= MERGE_DISTANCE &&
                    abs(it.y - warp.y) <= MERGE_DISTANCE
            }
            if (!duplicate) kept += warp
        }
        return kept
    }

    /** Toutes les Bases Secrètes du jeu, par lieu puis de haut en bas. */
    val secretBases: List<SecretBase> = MapPassages.secretBases(maps, warps)

    /** Entrées des Bases Secrètes dessinées sur une carte affichable (calque des Bases Secrètes). */
    fun secretBasesOf(mapId: Int): List<SecretBase> {
        val parts = partsOf(mapId).toSet()
        return secretBases.filter { it.entrance.mapId in parts }
    }

    /** Île qui apparaît sur une route de la carte du monde, null si le jeu n'en a pas. */
    val overlayIsland: OverlayIsland? = MapPassages.overlayIsland(maps, warps)

    /** L'île se dessine sur sa carte du monde tant qu'elle est le lieu sélectionné. */
    fun isIslandShown(mapId: Int, zoneId: Int?): Boolean =
        overlayIsland?.let { mapId == it.worldId && zoneId == it.islandId } == true

    /** Entrées dessinées : l'île affichée remplace son accès par le retour à la route. */
    fun displayedEntrances(mapId: Int, zoneId: Int?): List<MapWarp> {
        val island = overlayIsland ?: return entrancesOf(mapId)
        if (!isIslandShown(mapId, zoneId)) return entrancesOf(mapId)
        return entrancesOf(mapId).filter { it.id != island.show.id } + island.hide
    }

    /** Objets et personnages dessinés sur une carte affichable, avec ceux de l'île affichée. */
    fun displayedObjects(mapId: Int, zoneId: Int?): List<MapObject> {
        val parts = partsOf(mapId) + listOfNotNull(overlayIsland?.islandId?.takeIf { isIslandShown(mapId, zoneId) })
        return parts.flatMap { objects[it].orEmpty() }
    }

    /**
     * Warps vers les lieux accessibles depuis une ville, une route ou une carte intérieure (bâtiments, grottes,
     * étages, sorties), un par lieu. Depuis une ville ou une route, seules les cartes intérieures comptent.
     */
    fun accessibleFrom(mapId: Int): List<MapWarp> {
        val zone = maps[mapId] ?: return emptyList()
        val candidates = if (zone.parentId == null) entrancesOf(zone.id) else warps[zone.id].orEmpty()
        // Les Bases Secrètes ont leur propre calque et leur liste dans les astuces.
        return candidates.filter { it.kind != WarpKind.SECRET_BASE }.filter { warp ->
            val target = warp.targetMapId?.let { maps[it] } ?: return@filter false
            target.id != zone.id &&
                (displayedMapOf(zone.id)?.isWorld != true || displayedMapOf(target.id)?.isWorld != true)
        }.distinctBy { it.targetMapId }
    }

    /** Tous les objets et personnages du jeu, par identifiant. */
    val objectsById: Map<Int, MapObject> = objects.values.flatten().associateBy { it.id }

    /**
     * Où dessiner chaque objet : le centre de sa case, sauf quand plusieurs objets partagent une case de la même
     * carte affichée (personnages de deux étapes du scénario, objet caché sous un rocher) ; ils s'y écartent alors
     * côte à côte pour rester visibles et se toucher chacun.
     */
    val markerPositions: Map<Int, MarkerPosition> = objects.values.flatten()
        .groupBy { Triple(displayedMapOf(it.mapId)?.id, it.x, it.y) }
        .values
        .flatMap { shared -> spreadInCell(shared.sortedBy { it.id }) }
        .toMap()

    fun markerPosition(obj: MapObject): MarkerPosition = markerPositions[obj.id] ?: MarkerPosition(obj.x, obj.y)

    /** Carte (affichable ou ville, route) d'après son identifiant. */
    fun mapByIdentifier(identifier: String): MapInfo? = byIdentifier[identifier]

    /** Une entrée de recherche par lieu nommé, sans répéter une salle et le plan qui ne contient qu'elle. */
    fun searchableMaps(): List<MapInfo> = maps.values.filter { map ->
        if (map.isWorld) return@filter false
        val parent = maps[map.parentId]
        when {
            parent == null -> regionsOf(map.id).size != 1
            parent.isWorld -> true
            else -> regionsOf(parent.id).size == 1 || map.name != parent.name
        }
    }

    /**
     * Entrée sur la carte du monde de chaque carte intérieure : le warp de la carte du monde par lequel
     * on l'atteint en passant par le moins de cartes (Mont Sélénite sous-sol 2 → entrée du Mont Sélénite).
     */
    fun worldEntrances(): Map<Int, MapWarp> {
        val result = mutableMapOf<Int, MapWarp>()
        for ((target, entrance) in reachedBy) {
            var root = entrance
            val seen = mutableSetOf(target)
            while (!isWorld(displayedMapOf(root.mapId)?.id ?: root.mapId) && seen.add(root.mapId)) {
                root = reachedBy[displayedMapOf(root.mapId)?.id] ?: break
            }
            if (isWorld(displayedMapOf(root.mapId)?.id ?: root.mapId)) {
                partsOf(target).forEach { result[it] = root }
            }
        }
        return result
    }

    private val buildingOf: Map<Int, String> by lazy {
        sections.keys.associateWith { id -> checkNotNull(FloorLevel.parse(maps.getValue(id).identifier)).first }
    }

    /** Étages uniquement : les maisons et les zones d'un même niveau ne deviennent pas des badges. */
    fun floorsOf(mapId: Int, centerGroundId: Int? = null): List<MapFloor> {
        landscapeFloors[mapId]?.let { return it }
        val baseId = levelsOf(mapId).firstOrNull()?.mapId ?: mapId
        val display = displayedMapOf(baseId) ?: return emptyList()
        val upstairs = mapByIdentifier("pokecenter-2f-plan")
        val ground = if (display.id == upstairs?.id) {
            maps[centerGroundId ?: reachedBy[display.id]?.mapId]
        } else {
            display
        }
        if (upstairs != null && ground?.identifier?.endsWith("pokecenter-1f") == true) {
            return listOf(
                MapFloor(upstairs.id, FloorLevel.Storey(1), upstairs.name),
                MapFloor(ground.id, FloorLevel.Storey(0), ground.name)
            )
        }
        return landscapeFloors[display.id] ?: sections[display.id].orEmpty()
    }

    private val surfaceLevels = MapLevels.build(maps)

    fun levelsOf(mapId: Int): List<MapFloor> = surfaceLevels[mapId].orEmpty()

    private val landscapeFloors = MapLandscape.floors(maps)

    private val sections: Map<Int, List<MapFloor>> = MapSections.build(maps)

    /** Pour chaque carte intérieure, le warp par lequel on l'atteint en premier en partant de l'extérieur. */
    private val reachedBy: Map<Int, MapWarp> = reachedFromWorlds()

    private fun reachedFromWorlds(): Map<Int, MapWarp> {
        val result = mutableMapOf<Int, MapWarp>()
        val queue = ArrayDeque(worlds.flatMap { partsOf(it.id) })
        val seen = mutableSetOf<Int>()
        while (queue.isNotEmpty()) {
            val source = queue.removeFirst()
            if (!seen.add(source)) continue
            for (warp in warps[source].orEmpty()) {
                // Une carte modèle de Base Secrète a des dizaines d'entrées : aucune n'est la sienne.
                if (warp.kind == WarpKind.SECRET_BASE) continue
                val target = warp.targetMapId?.let(::displayedMapOf) ?: continue
                if (!target.isDisplayable || isWorld(target.id) || target.id in result) continue
                val origin = target.originMapId
                val sourceOrigin = maps[source]?.originMapId ?: displayedMapOf(source)?.originMapId ?: source
                if (origin != null && sourceOrigin != origin) continue
                result[target.id] = warp
                queue += partsOf(target.id)
            }
        }
        return result
    }

    /**
     * Entrée d'une carte intérieure dans le niveau du dessus : le warp (sur la ville, la route ou la carte
     * intérieure parente) qui y mène. Les étages d'un même bâtiment ont tous l'entrée du bâtiment : depuis le
     * 2e sous-sol du Mont Sélénite, on remonte directement à l'entrée du Mont Sélénite sur la Route 3.
     */
    fun parentEntrance(mapId: Int): MapWarp? {
        val displayId = displayedMapOf(mapId)?.id ?: return null
        val building = buildingOf[displayId]
        var warp = reachedBy[displayId] ?: return null
        val seen = mutableSetOf(mapId)
        while (building != null && buildingOf[displayedMapOf(warp.mapId)?.id] == building && seen.add(warp.mapId)) {
            warp = reachedBy[displayedMapOf(warp.mapId)?.id] ?: return null
        }
        return warp
    }

    private companion object {
        const val MERGE_DISTANCE = 32
    }
}
