package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.Composable
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlin.math.max
import kotlin.math.min
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.model.EncounterGroup
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetPokemonMapsUseCase
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveMapCatalogUseCase
import ovh.plrapps.mapcompose.api.BoundingBox
import ovh.plrapps.mapcompose.api.addLayer
import ovh.plrapps.mapcompose.api.addLazyLoader
import ovh.plrapps.mapcompose.api.addMarker
import ovh.plrapps.mapcompose.api.addPath
import ovh.plrapps.mapcompose.api.centroidX
import ovh.plrapps.mapcompose.api.centroidY
import ovh.plrapps.mapcompose.api.onMarkerClick
import ovh.plrapps.mapcompose.api.onTap
import ovh.plrapps.mapcompose.api.removeAllMarkers
import ovh.plrapps.mapcompose.api.removePath
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.api.scrollTo
import ovh.plrapps.mapcompose.api.setMapBackground
import ovh.plrapps.mapcompose.api.snapScrollTo
import ovh.plrapps.mapcompose.ui.state.MapState
import ovh.plrapps.mapcompose.ui.state.markers.model.RenderingStrategy

/** Calques activables de la carte. */
enum class MapLayer {
    WARPS,
    ITEMS,
    TRAINERS,
    POKEMON
}

/** Lieu vers lequel on peut aller : carte (ou ville, route) et point d'arrivée, en pixels de la carte affichée. */
data class MapPlace(val mapId: Int, val name: String, val x: Int? = null, val y: Int? = null)

/** Élément touché sur la carte, détaillé dans la fiche en bas d'écran. */
sealed interface MapSelection {
    data class Zone(
        val mapId: Int,
        val name: String,
        val places: List<MapPlace>,
        val loading: Boolean = true,
        val encounters: List<EncounterGroup> = emptyList()
    ) : MapSelection

    data class Object(val obj: MapObject) : MapSelection
}

/** Mode « surlignage » : lieux d'un Pokémon dans la version choisie. */
data class MapHighlight(val pokemonId: Int, val name: String, val places: List<MapPlace>)

data class MapUiState(
    val game: Game? = null,
    val map: GameMap? = null,
    val mapState: MapState? = null,
    /** Carte précédente, pour le bouton retour. */
    val previous: MapPlace? = null,
    val layers: Set<MapLayer> = setOf(MapLayer.WARPS),
    val selection: MapSelection? = null,
    val highlight: MapHighlight? = null,
    /** Pokémon introuvable sur les cartes de la version (message à afficher une fois). */
    val notFound: String? = null
)

/**
 * Carte du jeu choisi, affichée avec MapCompose : carte du monde de Kanto et cartes intérieures,
 * zones cliquables, calques (entrées, objets, dresseurs, Pokémon fixes) et surlignage des lieux d'un Pokémon.
 */
@HiltViewModel
class MapViewModel @Inject constructor(
    observeCatalog: ObserveMapCatalogUseCase,
    private val getMapEncounters: GetMapEncountersUseCase,
    private val getPokemonMaps: GetPokemonMapsUseCase,
    private val mapRequests: MapRequests,
    private val tiles: MapTiles
) : ViewModel() {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()

    private val loaded = MutableStateFlow<GameMaps?>(null)

    /** Cartes visitées, pour revenir en arrière (carte, centre de l'écran et zoom au moment de la quitter). */
    private val history = ArrayDeque<Stop>()

    /** Cartes où se trouve le Pokémon surligné, et entrée sur la carte du monde de chaque carte intérieure. */
    private var highlightedMaps: Set<Int> = emptySet()
    private var worldEntrances: Map<Int, MapWarp> = emptyMap()

    /** Chemins (surlignage) dessinés sur la carte affichée. */
    private val drawnPaths = mutableListOf<String>()

    private data class Stop(val mapId: Int, val x: Double, val y: Double, val scale: Double, val name: String)

    init {
        viewModelScope.launch {
            observeCatalog().collect { gameMaps ->
                loaded.value = gameMaps
                worldEntrances = gameMaps.catalog.worldEntrances()
                history.clear()
                _state.update { it.copy(game = gameMaps.game, selection = null, previous = null) }
                val current = _state.value.highlight
                if (current != null) {
                    highlight(current.pokemonId, current.name)
                } else {
                    gameMaps.catalog.world?.let { open(it.id, push = false) }
                }
            }
        }
        viewModelScope.launch {
            mapRequests.pending.filterNotNull().collect { request ->
                loaded.filterNotNull().first()
                when (request) {
                    is MapRequest.HighlightPokemon -> highlight(request.pokemonId, request.name)
                }
                mapRequests.consume(request)
            }
        }
    }

    private val catalog: MapCatalog? get() = loaded.value?.catalog

    // --- Navigation entre les cartes ------------------------------------------------------------

    /** Ouvre un lieu : carte intérieure, ou ville et route (sur la carte du monde). */
    fun openPlace(place: MapPlace) {
        _state.update { it.copy(selection = null) }
        open(place.mapId, place.x, place.y, push = true)
    }

    /** Revient à la carte précédente, là où on l'avait quittée. */
    fun back() {
        val stop = history.removeLastOrNull() ?: return
        _state.update { it.copy(selection = null) }
        show(stop.mapId, stop.x, stop.y, stop.scale)
    }

    fun dismissSelection() = _state.update { it.copy(selection = null) }

    fun notFoundShown() = _state.update { it.copy(notFound = null) }

    fun toggleLayer(layer: MapLayer) {
        _state.update { it.copy(layers = if (layer in it.layers) it.layers - layer else it.layers + layer) }
        refreshOverlays()
    }

    fun clearHighlight() {
        highlightedMaps = emptySet()
        _state.update { it.copy(highlight = null) }
        refreshOverlays()
    }

    /**
     * Affiche la carte qui contient `mapId`, centrée sur (x, y) en pixels si donnés, sinon sur la ville ou la route.
     * `push` : mémorise la carte actuelle pour le bouton retour.
     */
    private fun open(mapId: Int, x: Int? = null, y: Int? = null, push: Boolean) {
        val catalog = catalog ?: return
        val displayed = catalog.displayedMapOf(mapId) ?: return
        val target = catalog.maps[mapId] ?: return
        val focusX = x ?: (if (target.parentId != null) target.x + target.width / 2 else null)
        val focusY = y ?: (if (target.parentId != null) target.y + target.height / 2 else null)
        val current = _state.value
        val currentMap = current.map
        val currentState = current.mapState
        if (push && currentMap != null && currentState != null && currentMap.id != displayed.id) {
            history.addLast(
                Stop(currentMap.id, currentState.centroidX, currentState.centroidY, currentState.scale, currentMap.name)
            )
        }
        val nx = focusX?.let { it.toDouble() / displayed.width }
        val ny = focusY?.let { it.toDouble() / displayed.height }
        if (currentMap?.id == displayed.id && currentState != null) {
            // Même carte : on se déplace seulement.
            if (nx != null && ny != null) {
                viewModelScope.launch { currentState.scrollTo(nx, ny, max(currentState.scale, FOCUS_SCALE)) }
            }
            return
        }
        show(displayed.id, nx, ny, if (nx != null) FOCUS_SCALE else null)
    }

    /** Crée la carte affichée (MapCompose) ; position et zoom normalisés, ou carte entière si absents. */
    private fun show(mapId: Int, x: Double?, y: Double?, scale: Double?) {
        val catalog = catalog ?: return
        val map = catalog.gameMap(mapId) ?: return
        val isWorld = map.identifier == GameMap.WORLD
        val start = map.regions.firstOrNull { it.identifier == START_REGION }
        val startX = x ?: start?.let { it.centerX.toDouble() / map.width } ?: CENTER
        val startY = y ?: start?.let { it.centerY.toDouble() / map.height } ?: CENTER
        val mapState = MapState(map.levelCount, map.width, map.height, GameMap.TILE_SIZE) {
            scroll(startX, startY)
            scale(scale ?: if (isWorld) WORLD_SCALE else FOCUS_SCALE)
            maxScale(MAX_SCALE)
            // Pixels nets en zoom avant ; lissage seulement quand la carte est réduite.
            bitmapFilteringEnabled { state -> state.scale < 1.0 }
        }.apply {
            addLayer(tiles.provider(map))
            setMapBackground(MAP_BACKGROUND)
            addLazyLoader(LAZY_LOADER, padding = 64.dp)
            onTap { tapX, tapY -> handleTap(tapX, tapY) }
            onMarkerClick { id, _, _ -> handleMarkerClick(id) }
        }
        _state.value.mapState?.shutdown()
        _state.update {
            it.copy(
                map = map,
                mapState = mapState,
                previous = history.lastOrNull()?.let { stop ->
                    MapPlace(stop.mapId, stop.name)
                }
            )
        }
        refreshOverlays()
        // Carte intérieure ouverte sans point d'arrivée : on l'affiche en entier.
        if (!isWorld && x == null && scale == null) {
            viewModelScope.launch { mapState.snapScrollTo(BoundingBox(0.0, 0.0, 1.0, 1.0), Offset(0.1f, 0.1f)) }
        }
    }

    // --- Sélection ------------------------------------------------------------------------------

    private fun handleTap(x: Double, y: Double) {
        val catalog = catalog ?: return
        val map = _state.value.map ?: return
        val px = (x * map.width).toInt()
        val py = (y * map.height).toInt()
        val zone = if (map.regions.isEmpty()) map.id else map.regions.firstOrNull { it.contains(px, py) }?.id
        if (zone == null) {
            dismissSelection()
            return
        }
        selectZone(catalog, zone)
    }

    private fun selectZone(catalog: MapCatalog, zoneId: Int) {
        val game = loaded.value?.game ?: return
        val info = catalog.maps[zoneId] ?: return
        val selection = MapSelection.Zone(zoneId, info.name, places(catalog, info))
        _state.update { it.copy(selection = selection) }
        viewModelScope.launch {
            val encounters = getMapEncounters(game, catalog, zoneId).groupByMethod()
            val ready = selection.copy(loading = false, encounters = encounters)
            _state.update { if (it.selection == selection) it.copy(selection = ready) else it }
        }
    }

    /** Lieux accessibles depuis une ville, une route ou une carte intérieure (bâtiments, grottes, étages, sorties). */
    private fun places(catalog: MapCatalog, zone: MapInfo): List<MapPlace> {
        val warps = if (zone.parentId == null) catalog.entrancesOf(zone.id) else catalog.warps[zone.id].orEmpty()
        return warps.mapNotNull { warp ->
            val target = warp.targetMapId?.let { catalog.maps[it] } ?: return@mapNotNull null
            // Depuis une ville ou une route, seules les cartes intérieures sont des lieux à ouvrir.
            if (target.id == zone.id || (zone.parentId != null && target.parentId != null)) return@mapNotNull null
            MapPlace(target.id, target.name, warp.targetX, warp.targetY)
        }.distinctBy { it.mapId }
    }

    private fun handleMarkerClick(id: String) {
        val catalog = catalog ?: return
        val (prefix, value) = id.split(':', limit = 2).let { it[0] to it.getOrNull(1)?.toIntOrNull() }
        value ?: return
        when (prefix) {
            WARP, HIGHLIGHT_WARP -> {
                val warp = catalog.warps.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                val target = catalog.maps[warp.targetMapId ?: return] ?: return
                openPlace(MapPlace(target.id, target.name, warp.targetX, warp.targetY))
            }

            OBJECT, HIGHLIGHT_OBJECT -> {
                val obj = catalog.objects.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                _state.update { it.copy(selection = MapSelection.Object(obj)) }
            }
        }
    }

    // --- Surlignage ----------------------------------------------------------------------------

    /** Surligne les lieux d'un Pokémon et recentre la carte du monde sur eux. */
    private suspend fun highlight(pokemonId: Int, name: String) {
        val gameMaps = loaded.value ?: return
        val catalog = gameMaps.catalog
        val world = catalog.world ?: return
        highlightedMaps = getPokemonMaps(gameMaps.game, catalog, pokemonId)
        if (highlightedMaps.isEmpty()) {
            _state.update { it.copy(highlight = null, notFound = name) }
        } else {
            val maps = highlightedMaps.mapNotNull { catalog.maps[it] }.sortedBy { it.id }
            val places = maps.map { MapPlace(it.id, it.name) }
            _state.update { it.copy(highlight = MapHighlight(pokemonId, name, places), selection = null) }
        }
        history.clear()
        if (_state.value.map?.id == world.id) refreshOverlays() else show(world.id, null, null, null)
        focusOnHighlight(catalog, world)
    }

    /** Recentre la carte du monde sur les villes, routes et entrées surlignées. */
    private suspend fun focusOnHighlight(catalog: MapCatalog, world: MapInfo) {
        val mapState = _state.value.mapState ?: return
        val boxes = highlightedMaps.mapNotNull { catalog.maps[it] }.mapNotNull { map ->
            when {
                map.parentId == world.id -> Box(map.x, map.y, map.x + map.width, map.y + map.height)

                else -> worldEntrances[map.id]?.let {
                    Box(
                        it.x - ENTRANCE_MARGIN,
                        it.y - ENTRANCE_MARGIN,
                        it.x + ENTRANCE_MARGIN,
                        it.y + ENTRANCE_MARGIN
                    )
                }
            }
        }
        if (boxes.isEmpty()) return
        val area = BoundingBox(
            boxes.minOf { it.left }.toDouble() / world.width,
            boxes.minOf { it.top }.toDouble() / world.height,
            boxes.maxOf { it.right }.toDouble() / world.width,
            boxes.maxOf { it.bottom }.toDouble() / world.height
        )
        mapState.scrollTo(area, Offset(0.2f, 0.2f))
    }

    private data class Box(val left: Int, val top: Int, val right: Int, val bottom: Int)

    // --- Calques -------------------------------------------------------------------------------

    /** Redessine marqueurs et surlignage de la carte affichée (calques ou surlignage modifiés). */
    private fun refreshOverlays() {
        val catalog = catalog ?: return
        val map = _state.value.map ?: return
        val mapState = _state.value.mapState ?: return
        val layers = _state.value.layers
        mapState.removeAllMarkers()
        drawnPaths.forEach { mapState.removePath(it) }
        drawnPaths.clear()

        fun MapState.marker(id: String, x: Int, y: Int, lazy: Boolean = true, content: @Composable () -> Unit) =
            addMarker(
                id,
                x.toDouble() / map.width,
                y.toDouble() / map.height,
                relativeOffset = Offset(-0.5f, -0.5f),
                zIndex = if (lazy) 0f else 1f,
                renderingStrategy = if (lazy) RenderingStrategy.LazyLoading(LAZY_LOADER) else RenderingStrategy.Default,
                c = content
            )

        if (MapLayer.WARPS in layers) {
            catalog.entrancesOf(map.id).forEach { warp ->
                mapState.marker("$WARP:${warp.id}", warp.x, warp.y) { WarpMarker(mapState) }
            }
        }
        val objects = catalog.partsOf(map.id).flatMap { catalog.objects[it].orEmpty() }
        objects.filter { it.kind.layer in layers }.forEach { obj ->
            mapState.marker("$OBJECT:${obj.id}", obj.x, obj.y) {
                ObjectMarker(mapState, obj, catalog.versionGroupIdentifier)
            }
        }
        val pokemonId = _state.value.highlight?.pokemonId ?: return
        // Villes et routes surlignées sur la carte du monde, ou toute la carte intérieure.
        catalog.partsOf(map.id).filter { it in highlightedMaps }.mapNotNull { catalog.maps[it] }.forEach { part ->
            val whole = part.parentId == null
            val left = if (whole) 0.0 else part.x.toDouble() / map.width
            val top = if (whole) 0.0 else part.y.toDouble() / map.height
            val right = if (whole) 1.0 else min(1.0, (part.x + part.width).toDouble() / map.width)
            val bottom = if (whole) 1.0 else min(1.0, (part.y + part.height).toDouble() / map.height)
            val id = "$HIGHLIGHT_PATH:${part.id}"
            mapState.addPath(
                id,
                width = 3.dp,
                color = HIGHLIGHT_COLOR,
                fillColor = HIGHLIGHT_COLOR.copy(alpha = 0.25f)
            ) {
                addPoints(listOf(left to top, right to top, right to bottom, left to bottom, left to top))
            }
            drawnPaths += id
        }
        // Entrées menant aux cartes intérieures surlignées.
        val entrances = if (map.identifier == GameMap.WORLD) {
            highlightedMaps.mapNotNull { worldEntrances[it] }
        } else {
            catalog.entrancesOf(map.id).filter { it.targetMapId in highlightedMaps }
        }
        entrances.distinctBy { it.id }.forEach { warp ->
            mapState.marker("$HIGHLIGHT_WARP:${warp.id}", warp.x, warp.y, lazy = false) { HighlightMarker() }
        }
        objects.filter { it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId }.forEach { obj ->
            mapState.marker("$HIGHLIGHT_OBJECT:${obj.id}", obj.x, obj.y, lazy = false) { HighlightMarker() }
        }
    }

    private val MapObjectKind.layer: MapLayer?
        get() = when (this) {
            MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> MapLayer.ITEMS
            MapObjectKind.TRAINER -> MapLayer.TRAINERS
            MapObjectKind.POKEMON -> MapLayer.POKEMON
            MapObjectKind.NPC -> null
        }

    override fun onCleared() {
        _state.value.mapState?.shutdown()
    }

    private companion object {
        const val START_REGION = "pallet-town"
        const val WORLD_SCALE = 2.0
        const val FOCUS_SCALE = 4.0
        const val MAX_SCALE = 12.0
        const val CENTER = 0.5
        const val ENTRANCE_MARGIN = 48
        const val LAZY_LOADER = "lazy"
        const val WARP = "w"
        const val OBJECT = "o"
        const val HIGHLIGHT_WARP = "hw"
        const val HIGHLIGHT_OBJECT = "ho"
        const val HIGHLIGHT_PATH = "hp"
        val MAP_BACKGROUND = Color(0xFF202028)
    }
}
