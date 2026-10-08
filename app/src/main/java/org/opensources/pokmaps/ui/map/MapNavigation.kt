package org.opensources.pokmaps.ui.map

import android.content.res.Resources
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlin.math.max
import kotlin.math.sqrt
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.map.MapZoom
import org.opensources.pokmaps.domain.map.MarkerSizing
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import ovh.plrapps.mapcompose.api.BoundingBox
import ovh.plrapps.mapcompose.api.addLayer
import ovh.plrapps.mapcompose.api.addLazyLoader
import ovh.plrapps.mapcompose.api.centroidX
import ovh.plrapps.mapcompose.api.centroidY
import ovh.plrapps.mapcompose.api.getLayoutSizeFlow
import ovh.plrapps.mapcompose.api.minimumScaleMode
import ovh.plrapps.mapcompose.api.onMarkerClick
import ovh.plrapps.mapcompose.api.onTap
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.api.scrollTo
import ovh.plrapps.mapcompose.api.setMapBackground
import ovh.plrapps.mapcompose.api.setScrollOffsetRatio
import ovh.plrapps.mapcompose.api.snapScrollTo
import ovh.plrapps.mapcompose.ui.layout.Fit
import ovh.plrapps.mapcompose.ui.layout.Forced
import ovh.plrapps.mapcompose.ui.state.MapState

/**
 * Carte affichée (MapCompose) et déplacements entre les cartes : entrées, étages, retour au niveau du dessus,
 * touches sur la carte, et position conservée au changement de version.
 */
internal class MapNavigation(
    private val session: MapSession,
    private val selection: MapSelection,
    private val getMapTiles: GetMapTilesUseCase
) {
    /** Dernier zoom de chaque carte affichée, retrouvé en y revenant par le bouton retour. */
    private val scales = mutableMapOf<Int, Double>()

    /** Suit la taille de la vue pour le zoom minimal de la carte du monde affichée ; arrêté à son remplacement. */
    private var viewportJob: Job? = null
    private var initialPosition: Position? = null
    private var positioned = false
    private var centerGroundId: Int? = null

    /** Oublie les zooms mémorisés (les cartes du nouveau jeu sont différentes). */
    fun forgetScales() {
        scales.clear()
        centerGroundId = null
    }

    fun selectWorld(mapId: Int) {
        val catalog = session.catalog ?: return
        if (!catalog.isWorld(mapId)) return
        show(mapId, null, null, scales[mapId])
    }

    /** Ouvre un lieu : carte intérieure, ou ville et route (sur la carte du monde). */
    fun openPlace(place: MapPlace) {
        session.update { it.copy(detail = null, zoneListOpen = false) }
        val target = session.catalog?.displayedMapOf(place.mapId)
        if (target != null && !target.isWorld && target.id != session.current.map?.id) {
            open(place.mapId)
        } else {
            open(place.mapId, place.x, place.y)
        }
    }

    /**
     * Remonte d'un niveau : d'un étage ou d'une carte intérieure vers le bâtiment, la ville ou la route qui la
     * contient (centré sur son entrée), quel que soit le chemin suivi pour y arriver. Sur la carte du monde, le
     * lieu sélectionné est désélectionné.
     */
    fun back() {
        val catalog = session.catalog ?: return
        val map = session.current.map ?: return
        session.update { it.copy(detail = null, zoneListOpen = false) }
        if (map.isWorld) {
            selection.clearZone()
            return
        }
        if (map.identifier == "pokecenter-2f-plan" && centerGroundId != null) {
            centerGroundId?.let { open(it) }
            return
        }
        val entrance = catalog.parentEntrance(map.id)
        if (entrance == null) {
            val origin = catalog.maps[map.id]?.originMapId ?: catalog.worldOf(map.id)?.id
            origin?.let { open(it) }
            return
        }
        val displayed = catalog.displayedMapOf(entrance.mapId) ?: return
        if (!displayed.isWorld && catalog.regionsOf(displayed.id).isNotEmpty()) {
            open(entrance.mapId)
        } else {
            open(entrance.mapId, entrance.x, entrance.y, scale = scales[displayed.id])
        }
    }

    /** Change d'étage : même vue si les deux étages ont la même taille, sinon l'étage entier. */
    fun selectFloor(mapId: Int) {
        val catalog = session.catalog ?: return
        val map = session.current.map ?: return
        val mapState = session.current.mapState ?: return
        if (mapId == map.id) return
        val target = catalog.maps[mapId]?.takeIf { it.isDisplayable } ?: return
        session.update { it.copy(detail = null, zoneListOpen = false) }
        if (target.width == map.width && target.height == map.height) {
            show(target.id, mapState.centroidX, mapState.centroidY, mapState.scale)
            selection.selectZone(catalog, target.id)
        } else {
            open(target.id)
        }
    }

    /** Ouvre la carte d'un objet ou d'un personnage (son bâtiment), centrée sur lui, avec sa fiche. */
    fun focusObject(obj: MapObject) {
        session.update { it.copy(detail = null, zoneListOpen = false) }
        open(obj.mapId, obj.x, obj.y)
        session.updateOverlays { it.copy(focusedObjectId = obj.id) }
        selection.showObject(obj)
        session.refreshOverlays()
    }

    /**
     * Affiche la carte qui contient `mapId`, centrée sur (x, y) en pixels si donnés, sinon sur la ville ou la route,
     * au zoom `scale` (zoom rapproché par défaut), et sélectionne ce lieu.
     */
    fun open(mapId: Int, x: Int? = null, y: Int? = null, scale: Double? = null) {
        val catalog = session.catalog ?: return
        val displayed = catalog.displayedMapOf(mapId) ?: return
        val target = catalog.maps[mapId] ?: return
        val focusX = x ?: (if (target.parentId != null && displayed.isWorld) target.x + target.width / 2 else null)
        val focusY = y ?: (if (target.parentId != null && displayed.isWorld) target.y + target.height / 2 else null)
        val currentMap = session.current.map
        val currentState = session.current.mapState
        val nx = focusX?.let { it.toDouble() / displayed.width }
        val ny = focusY?.let { it.toDouble() / displayed.height }
        if (currentMap?.id == displayed.id && currentState != null) {
            // Même carte : on se déplace seulement.
            if (nx != null && ny != null) {
                session.launch { currentState.scrollTo(nx, ny, scale ?: max(currentState.scale, FOCUS_SCALE)) }
            }
        } else {
            show(displayed.id, nx, ny, if (nx != null) scale ?: FOCUS_SCALE else null)
        }
        // Ville, route ou carte intérieure : son contenu s'affiche sur la carte.
        if (catalog.isWorld(target.id)) selection.clearZone() else selection.selectZone(catalog, target.id)
    }

    /** Crée la carte affichée (MapCompose) ; position et zoom normalisés, ou carte entière si absents. */
    fun show(mapId: Int, x: Double?, y: Double?, scale: Double?) {
        val catalog = session.catalog ?: return
        val map = catalog.gameMap(mapId) ?: return
        if (map.identifier == "pokecenter-2f-plan") {
            val previous = session.current.map
            centerGroundId = previous?.takeIf { it.identifier.endsWith("pokecenter-1f") }?.id
        }
        val isWorld = map.isWorld
        val arrival = startingPosition(map, x, y, scale)
        val mapState = createMapState(map, arrival)
        retire(session.current)
        initialPosition = arrival
        positioned = false
        followViewport(map, mapState)
        val objects = catalog.partsOf(map.id).flatMap { catalog.objects[it].orEmpty() }
        session.updateOverlays {
            it.copy(
                wildMarkers = emptyList(),
                focusedObjectId = null,
                objectScales = MarkerSizing.objectScales(objects)
            )
        }
        val parent = if (isWorld) {
            null
        } else {
            centerGroundId?.takeIf { map.identifier == "pokecenter-2f-plan" }?.let { catalog.maps[it] }
                ?: catalog.parentEntrance(map.id)?.let { catalog.maps[it.mapId] }
                ?: catalog.maps[catalog.maps[map.id]?.originMapId] ?: catalog.worldOf(map.id)
        }
        session.update {
            it.copy(
                map = map,
                hasConnections = catalog.connectionsOf(map.id).isNotEmpty(),
                worldId = catalog.worldOf(map.id)?.id,
                mapState = mapState,
                zone = null,
                detail = null,
                zoneListOpen = false,
                parent = parent?.let { place -> MapPlace(place.id, place.name) },
                floors = catalog.floorsOf(map.id, centerGroundId)
            )
        }
        session.refreshOverlays()
        // Carte intérieure ouverte sans point d'arrivée : on l'affiche en entier.
        if (!isWorld && x == null && scale == null) {
            session.launch { mapState.snapScrollTo(BoundingBox(0.0, 0.0, 1.0, 1.0), Offset(0.1f, 0.1f)) }
        }
    }

    private fun startingPosition(map: GameMap, x: Double?, y: Double?, scale: Double?): Position {
        val start = map.regions.firstOrNull { it.id == map.startRegionId }
        return Position(
            map.identifier,
            null,
            x ?: start?.let { it.centerX.toDouble() / map.width } ?: CENTER,
            y ?: start?.let { it.centerY.toDouble() / map.height } ?: CENTER,
            scale ?: if (map.isWorld) WORLD_SCALE else FOCUS_SCALE
        )
    }

    private fun createMapState(map: GameMap, position: Position): MapState =
        MapState(map.levelCount, map.width, map.height, GameMap.TILE_SIZE) {
            scroll(position.x, position.y)
            scale(position.scale)
            minimumScaleMode(
                when {
                    map.isWorld -> Fit
                    map.regions.isNotEmpty() -> Forced(MIN_PLAN_SCALE)
                    else -> Forced(MIN_INDOOR_SCALE)
                }
            )
            maxScale(MAX_SCALE)
            // Pixels nets en zoom avant ; lissage seulement quand la carte est réduite.
            bitmapFilteringEnabled { state -> state.scale < 1.0 }
        }.apply {
            // Les bords de la carte peuvent venir jusqu'au milieu de l'écran : tout lieu peut y être centré.
            setScrollOffsetRatio(EDGE_SCROLL_RATIO, EDGE_SCROLL_RATIO)
            addLayer(getMapTiles(map))
            setMapBackground(MAP_BACKGROUND)
            addLazyLoader(MapMarkerIds.LAZY_LOADER, padding = 64.dp)
            onTap { tapX, tapY -> handleTap(tapX, tapY) }
            onMarkerClick { id, _, _ -> handleMarkerClick(id) }
        }

    /**
     * Carte du monde : son zoom minimal suit la taille de la vue (rotation, barres), un peu au-delà de la carte
     * entière ([MapZoom]). Avant la première mesure, la carte entière (Fit) sert de minimum.
     */
    private fun followViewport(map: GameMap, mapState: MapState) {
        viewportJob?.cancel()
        viewportJob = session.launch {
            mapState.getLayoutSizeFlow().collect { size ->
                if (size.width <= 0 || size.height <= 0) return@collect
                if (map.isWorld || map.regions.isNotEmpty()) {
                    MapZoom.minScale(size.width, size.height, map.width, map.height)?.let {
                        mapState.minimumScaleMode = Forced(it)
                    }
                }
                if (!positioned) {
                    initialPosition?.let { mapState.snapScrollTo(it.x, it.y) }
                    positioned = true
                }
            }
        }
    }

    /** Mémorise le zoom de la carte quittée, qui s'efface en fondu avant d'être arrêtée. */
    private fun retire(current: MapUiState) {
        val oldState = current.mapState ?: return
        current.map?.let { scales[it.id] = oldState.scale }
        session.launch {
            delay(SHUTDOWN_DELAY_MS)
            oldState.shutdown()
        }
    }

    private fun handleTap(x: Double, y: Double) {
        val catalog = session.catalog ?: return
        val map = session.current.map ?: return
        val mapState = session.current.mapState ?: return
        val px = (x * map.width).toInt()
        val py = (y * map.height).toInt()
        // Une entrée touchée à peu près (à un doigt près) fait entrer, sans viser exactement son marqueur.
        val tolerance = WARP_TOUCH_RADIUS_DP * Resources.getSystem().displayMetrics.density / mapState.scale
        // Vue très éloignée : la tolérance couvrirait plusieurs bâtiments, seuls les marqueurs touchés comptent.
        val warp = visibleEntrances(catalog, map.id).minByOrNull { distance(it.x, it.y, px, py) }
            ?.takeIf { mapState.scale >= WARP_TOUCH_MIN_SCALE }
        if (warp != null && distance(warp.x, warp.y, px, py) <= tolerance) {
            enter(catalog, warp)
            return
        }
        if (session.current.detail != null) {
            selection.dismissDetail()
            return
        }
        if (map.regions.isEmpty()) return
        val zone = map.regions.firstOrNull { it.contains(px, py) }?.id
        if (zone == null) {
            selection.clearZone()
        } else if (zone != session.current.zone?.mapId) {
            selection.selectZone(catalog, zone)
            focusOnZone(catalog, zone)
        }
    }

    private fun distance(ax: Int, ay: Int, bx: Int, by: Int): Double {
        val dx = (ax - bx).toDouble()
        val dy = (ay - by).toDouble()
        return sqrt(dx * dx + dy * dy)
    }

    /** Entrées dessinées sur la carte (calque des entrées affiché). */
    private fun visibleEntrances(catalog: MapCatalog, mapId: Int): List<MapWarp> =
        if (MapLayer.WARPS in session.current.layers) catalog.entrancesOf(mapId) else emptyList()

    private fun enter(catalog: MapCatalog, warp: MapWarp) {
        val target = catalog.maps[warp.targetMapId ?: return] ?: return
        openPlace(MapPlace(target.id, target.name, warp.targetX, warp.targetY))
    }

    /** Rapproche la vue d'une ville ou d'une route touchée sur la carte du monde, pour voir son contenu. */
    private fun focusOnZone(catalog: MapCatalog, zoneId: Int) {
        val map = session.current.map ?: return
        if (!map.isWorld) return
        val mapState = session.current.mapState ?: return
        val zone = catalog.maps[zoneId]?.takeIf { it.parentId != null } ?: return
        if (mapState.scale >= ZONE_FOCUS_MIN_SCALE) return
        val area = BoundingBox(
            zone.x.toDouble() / map.width,
            zone.y.toDouble() / map.height,
            (zone.x + zone.width).toDouble() / map.width,
            (zone.y + zone.height).toDouble() / map.height
        )
        session.launch { mapState.scrollTo(area, Offset(0.1f, 0.1f)) }
    }

    private fun handleMarkerClick(id: String) {
        val catalog = session.catalog ?: return
        val parts = id.split(':')
        val value = parts.getOrNull(1)?.toIntOrNull() ?: return
        when (parts[0]) {
            MapMarkerIds.WARP, MapMarkerIds.HIGHLIGHT_WARP -> {
                val warp = catalog.warps.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                enter(catalog, warp)
            }

            MapMarkerIds.OBJECT, MapMarkerIds.HIGHLIGHT_OBJECT -> {
                val obj = catalog.objects.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                selection.showObject(obj)
            }

            MapMarkerIds.WILD -> {
                val index = parts.getOrNull(2)?.toIntOrNull() ?: return
                val marker = session.overlays.wildMarkers.getOrNull(index) ?: return
                selection.showWildPokemon(value, marker.mapId)
            }
        }
    }

    // --- Changement de version -----------------------------------------------------------------

    /** Carte affichée, lieu sélectionné, centre de l'écran et zoom, par identifiants (communs aux jeux). */
    data class Position(
        val mapIdentifier: String,
        val zoneIdentifier: String?,
        val x: Double,
        val y: Double,
        val scale: Double
    )

    fun currentPosition(): Position? {
        val catalog = session.catalog ?: return null
        val map = session.current.map ?: return null
        val mapState = session.current.mapState ?: return null
        val zone = session.current.zone?.let { catalog.maps[it.mapId]?.identifier }
        if (!positioned) return initialPosition?.copy(zoneIdentifier = zone)
        return Position(map.identifier, zone, mapState.centroidX, mapState.centroidY, mapState.scale)
    }

    /** Reste à la même position dans le nouveau jeu ; false si la carte n'y existe pas. */
    fun stay(catalog: MapCatalog, position: Position, sameMaps: Boolean): Boolean {
        val map = catalog.maps.values.firstOrNull { it.identifier == position.mapIdentifier && it.isDisplayable }
            ?: return false
        // Mêmes cartes (Rouge ↔ Bleu) : la carte affichée reste, seules les rencontres changent.
        if (!sameMaps || session.current.map?.id != map.id) {
            show(map.id, position.x, position.y, position.scale)
        }
        val zone = position.zoneIdentifier?.let(catalog::mapByIdentifier)
            ?.takeIf { catalog.displayedMapOf(it.id)?.id == map.id }
        if (zone != null) selection.selectZone(catalog, zone.id) else selection.clearZone()
        return true
    }

    private companion object {
        const val WORLD_SCALE = 2.0
        const val FOCUS_SCALE = 4.0
        const val MIN_INDOOR_SCALE = 0.5
        const val MIN_PLAN_SCALE = 0.05
        const val ZONE_FOCUS_MIN_SCALE = 3.0
        const val MAX_SCALE = 12.0
        const val CENTER = 0.5
        const val EDGE_SCROLL_RATIO = 0.5f
        const val WARP_TOUCH_RADIUS_DP = 24f
        const val WARP_TOUCH_MIN_SCALE = 1.0
        const val SHUTDOWN_DELAY_MS = 600L
        val MAP_BACKGROUND = Color(0xFF202028)
    }
}
