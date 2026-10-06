package org.opensources.pokmaps.ui.map

import android.content.res.Resources
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
import kotlin.math.sqrt
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.map.MarkerSizing
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetPokemonMapsUseCase
import org.opensources.pokmaps.domain.usecase.MapLayersUseCase
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
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

/**
 * Carte du jeu choisi, affichée avec MapCompose : carte du monde de Kanto et cartes intérieures,
 * lieux cliquables (leur contenu s'affiche sur la carte), calques et surlignage des lieux d'un Pokémon.
 */
@HiltViewModel
class MapViewModel @Inject constructor(
    observeCatalog: ObserveMapCatalogUseCase,
    private val getMapEncounters: GetMapEncountersUseCase,
    private val getPokemonMaps: GetPokemonMapsUseCase,
    private val getObjectDetails: GetMapObjectDetailsUseCase,
    private val mapRequests: MapRequests,
    private val mapLayers: MapLayersUseCase,
    observeCollection: ObserveCollectionUseCase,
    displaySettings: DisplaySettings,
    private val tiles: MapTiles
) : ViewModel() {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()

    private val loaded = MutableStateFlow<GameMaps?>(null)

    /** Dernier zoom de chaque carte affichée, retrouvé en y revenant par le bouton retour. */
    private val scales = mutableMapOf<Int, Double>()

    /** Cartes où se trouve le Pokémon surligné, et entrée sur la carte du monde de chaque carte intérieure. */
    private var highlightedMaps: Set<Int> = emptySet()

    /** Personnages qui donnent ou échangent le Pokémon surligné. */
    private var highlightedObjects: Set<Int> = emptySet()

    /** Objet ou personnage mis en évidence (ouvert depuis une fiche). */
    private var focusedObjectId: Int? = null
    private var worldEntrances: Map<Int, MapWarp> = emptyMap()

    /** Pokémon sauvages dessinés pour le lieu sélectionné. */
    private var wildMarkers: List<WildMarker> = emptyList()

    /** Taille des objets, personnages et Pokémon fixes de la carte affichée, selon la place autour d'eux. */
    private var objectScales: Map<Int, Float> = emptyMap()

    /** L'écran de la carte a déjà été affiché une fois (voir [onScreenShown]). */
    private var screenShown = false

    init {
        viewModelScope.launch {
            observeCatalog().collect { gameMaps ->
                val previous = loaded.value
                // Changement de version : on reste là où on est si la carte existe aussi dans le nouveau jeu
                // (Rouge et Bleu partagent leurs cartes, Jaune a presque toutes les mêmes), pour comparer.
                val position = currentPosition()
                loaded.value = gameMaps
                worldEntrances = gameMaps.catalog.worldEntrances()
                val sameMaps = previous?.catalog === gameMaps.catalog
                if (!sameMaps) scales.clear()
                _state.update { it.copy(game = gameMaps.game, detail = null, zoneListOpen = false) }
                val stayed = position != null && stay(gameMaps.catalog, position, sameMaps)
                val current = _state.value.highlight
                when {
                    current != null -> highlight(current.pokemonId, current.name, move = !stayed)
                    !stayed -> gameMaps.catalog.world?.let { open(it.id) }
                }
            }
        }
        viewModelScope.launch {
            mapRequests.pending.filterNotNull().collect { request ->
                loaded.filterNotNull().first()
                when (request) {
                    is MapRequest.HighlightPokemon -> highlight(request.pokemonId, request.name)

                    is MapRequest.OpenPlace -> catalog?.mapByIdentifier(request.mapIdentifier)?.let { map ->
                        _state.update { it.copy(detail = null, zoneListOpen = false) }
                        open(map.id)
                    }

                    is MapRequest.FocusObject -> catalog?.objectsById?.get(request.objectId)?.let { focusObject(it) }
                }
                mapRequests.consume(request)
            }
        }
        viewModelScope.launch {
            mapLayers.layers.collect { layers ->
                if (layers == _state.value.layers) return@collect
                _state.update { it.copy(layers = layers) }
                refreshOverlays()
            }
        }
        viewModelScope.launch {
            observeCollection().collect { collection ->
                _state.update { it.copy(caught = collection.caught) }
            }
        }
        viewModelScope.launch {
            displaySettings.mapAnimatedSprites.collect { animated ->
                if (animated == _state.value.animatedSprites) return@collect
                _state.update { it.copy(animatedSprites = animated) }
                refreshOverlays()
            }
        }
    }

    /**
     * L'écran de la carte revient (après le Pokédex, une fiche…) : la carte MapCompose, restée en mémoire alors
     * que son affichage était détruit, est recréée à la même position, avec le même lieu sélectionné. Sans cela,
     * ses gestes gardent l'état de l'ancien affichage et les touches ne sélectionnent plus d'autre lieu.
     */
    fun onScreenShown() {
        if (!screenShown) {
            screenShown = true
            return
        }
        val current = _state.value
        val map = current.map ?: return
        val mapState = current.mapState ?: return
        val markers = wildMarkers
        val focused = focusedObjectId
        show(map.id, mapState.centroidX, mapState.centroidY, mapState.scale)
        wildMarkers = markers
        focusedObjectId = focused
        _state.update { it.copy(zone = current.zone, detail = current.detail, zoneListOpen = current.zoneListOpen) }
        refreshOverlays()
    }

    private val catalog: MapCatalog? get() = loaded.value?.catalog

    // --- Navigation entre les cartes ------------------------------------------------------------

    /** Ouvre un lieu : carte intérieure, ou ville et route (sur la carte du monde). */
    fun openPlace(place: MapPlace) {
        _state.update { it.copy(detail = null, zoneListOpen = false) }
        open(place.mapId, place.x, place.y)
    }

    /**
     * Remonte d'un niveau : d'un étage ou d'une carte intérieure vers le bâtiment, la ville ou la route qui la
     * contient (centré sur son entrée), quel que soit le chemin suivi pour y arriver. Sur la carte du monde, le
     * lieu sélectionné est désélectionné.
     */
    fun back() {
        val catalog = catalog ?: return
        val map = _state.value.map ?: return
        _state.update { it.copy(detail = null, zoneListOpen = false) }
        if (map.identifier == GameMap.WORLD) {
            clearZone()
            return
        }
        val entrance = catalog.parentEntrance(map.id)
        if (entrance == null) {
            catalog.world?.let { open(it.id) }
            return
        }
        val displayed = catalog.displayedMapOf(entrance.mapId) ?: return
        open(entrance.mapId, entrance.x, entrance.y, scale = scales[displayed.id])
    }

    /** Change d'étage : même vue si les deux étages ont la même taille, sinon l'étage entier. */
    fun selectFloor(mapId: Int) {
        val catalog = catalog ?: return
        val current = _state.value
        val map = current.map ?: return
        val mapState = current.mapState ?: return
        if (mapId == map.id) return
        val target = catalog.maps[mapId]?.takeIf { it.isDisplayable } ?: return
        _state.update { it.copy(detail = null, zoneListOpen = false) }
        if (target.width == map.width && target.height == map.height) {
            show(target.id, mapState.centroidX, mapState.centroidY, mapState.scale)
            selectZone(catalog, target.id)
        } else {
            open(target.id)
        }
    }

    fun dismissDetail() {
        _state.update { it.copy(detail = null) }
        if (focusedObjectId != null) {
            focusedObjectId = null
            refreshOverlays()
        }
    }

    fun openZoneList() = _state.update { it.copy(zoneListOpen = true, detail = null) }

    fun closeZoneList() = _state.update { it.copy(zoneListOpen = false) }

    /** Désélectionne la ville ou la route (une carte intérieure reste toujours sélectionnée). */
    fun clearZone() {
        val map = _state.value.map
        if (map != null && map.identifier != GameMap.WORLD) return
        wildMarkers = emptyList()
        _state.update { it.copy(zone = null, detail = null, zoneListOpen = false) }
        refreshOverlays()
    }

    fun notFoundShown() = _state.update { it.copy(notFound = null) }

    fun toggleLayer(layer: MapLayer) {
        val layers = _state.value.layers.let { if (layer in it) it - layer else it + layer }
        _state.update { it.copy(layers = layers) }
        refreshOverlays()
        viewModelScope.launch { mapLayers.set(layers) }
    }

    fun clearHighlight() {
        highlightedMaps = emptySet()
        highlightedObjects = emptySet()
        _state.update { it.copy(highlight = null) }
        refreshOverlays()
    }

    /** Ouvre la fiche détaillée d'un Pokémon sauvage depuis la liste du lieu. */
    fun showWildPokemon(pokemonId: Int) {
        val zone = _state.value.zone ?: return
        val encounters = zone.encounters.filter { it.pokemonId == pokemonId }
        val name = encounters.firstOrNull()?.pokemonName ?: return
        _state.update { it.copy(detail = MapDetail.WildPokemon(pokemonId, name, encounters.groupByMethod())) }
    }

    /**
     * Affiche la carte qui contient `mapId`, centrée sur (x, y) en pixels si donnés, sinon sur la ville ou la route,
     * au zoom `scale` (zoom rapproché par défaut), et sélectionne ce lieu.
     */
    private fun open(mapId: Int, x: Int? = null, y: Int? = null, scale: Double? = null) {
        val catalog = catalog ?: return
        val displayed = catalog.displayedMapOf(mapId) ?: return
        val target = catalog.maps[mapId] ?: return
        val focusX = x ?: (if (target.parentId != null) target.x + target.width / 2 else null)
        val focusY = y ?: (if (target.parentId != null) target.y + target.height / 2 else null)
        val currentMap = _state.value.map
        val currentState = _state.value.mapState
        val nx = focusX?.let { it.toDouble() / displayed.width }
        val ny = focusY?.let { it.toDouble() / displayed.height }
        if (currentMap?.id == displayed.id && currentState != null) {
            // Même carte : on se déplace seulement.
            if (nx != null && ny != null) {
                viewModelScope.launch { currentState.scrollTo(nx, ny, scale ?: max(currentState.scale, FOCUS_SCALE)) }
            }
        } else {
            show(displayed.id, nx, ny, if (nx != null) scale ?: FOCUS_SCALE else null)
        }
        // Ville, route ou carte intérieure : son contenu s'affiche sur la carte.
        if (target.id == catalog.world?.id) clearZone() else selectZone(catalog, target.id)
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
            addLazyLoader(MapMarkerIds.LAZY_LOADER, padding = 64.dp)
            onTap { tapX, tapY -> handleTap(tapX, tapY) }
            onMarkerClick { id, _, _ -> handleMarkerClick(id) }
        }
        _state.value.let { current ->
            val oldState = current.mapState ?: return@let
            current.map?.let { scales[it.id] = oldState.scale }
            // L'ancienne carte s'efface en fondu avant d'être arrêtée.
            viewModelScope.launch {
                delay(SHUTDOWN_DELAY_MS)
                oldState.shutdown()
            }
        }
        wildMarkers = emptyList()
        focusedObjectId = null
        objectScales = MarkerSizing.objectScales(catalog.partsOf(map.id).flatMap { catalog.objects[it].orEmpty() })
        val parent = when {
            isWorld -> null
            else -> catalog.parentEntrance(map.id)?.let { catalog.maps[it.mapId] } ?: catalog.world
        }
        _state.update {
            it.copy(
                map = map,
                mapState = mapState,
                zone = null,
                detail = null,
                zoneListOpen = false,
                parent = parent?.let { place -> MapPlace(place.id, place.name) },
                floors = catalog.floorsOf(map.id)
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
        val mapState = _state.value.mapState ?: return
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
        if (_state.value.detail != null) {
            dismissDetail()
            return
        }
        if (map.regions.isEmpty()) return
        val zone = map.regions.firstOrNull { it.contains(px, py) }?.id
        if (zone == null) {
            clearZone()
        } else if (zone != _state.value.zone?.mapId) {
            selectZone(catalog, zone)
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
        if (MapLayer.WARPS in _state.value.layers) catalog.entrancesOf(mapId) else emptyList()

    private fun enter(catalog: MapCatalog, warp: MapWarp) {
        val target = catalog.maps[warp.targetMapId ?: return] ?: return
        openPlace(MapPlace(target.id, target.name, warp.targetX, warp.targetY))
    }

    private fun selectZone(catalog: MapCatalog, zoneId: Int) {
        val game = loaded.value?.game ?: return
        val info = catalog.maps[zoneId] ?: return
        val zone = MapZone(zoneId, info.name, MapZoneContent.places(catalog, info))
        wildMarkers = emptyList()
        _state.update { it.copy(zone = zone, detail = null, zoneListOpen = false) }
        refreshOverlays()
        viewModelScope.launch {
            val encounters = getMapEncounters(game, catalog, zoneId)
            val ready = zone.copy(loading = false, encounters = encounters)
            if (_state.value.zone != zone) return@launch
            wildMarkers = MapZoneContent.wildMarkers(catalog, info, encounters)
            _state.update { it.copy(zone = ready) }
            refreshOverlays()
        }
    }

    /** Rapproche la vue d'une ville ou d'une route touchée sur la carte du monde, pour voir son contenu. */
    private fun focusOnZone(catalog: MapCatalog, zoneId: Int) {
        val map = _state.value.map ?: return
        val mapState = _state.value.mapState ?: return
        val zone = catalog.maps[zoneId]?.takeIf { it.parentId != null } ?: return
        if (mapState.scale >= ZONE_FOCUS_MIN_SCALE) return
        val area = BoundingBox(
            zone.x.toDouble() / map.width,
            zone.y.toDouble() / map.height,
            (zone.x + zone.width).toDouble() / map.width,
            (zone.y + zone.height).toDouble() / map.height
        )
        viewModelScope.launch { mapState.scrollTo(area, Offset(0.1f, 0.1f)) }
    }

    private fun handleMarkerClick(id: String) {
        val catalog = catalog ?: return
        val parts = id.split(':')
        val prefix = parts[0]
        val value = parts.getOrNull(1)?.toIntOrNull() ?: return
        when (prefix) {
            MapMarkerIds.WARP, MapMarkerIds.HIGHLIGHT_WARP -> {
                val warp = catalog.warps.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                enter(catalog, warp)
            }

            MapMarkerIds.OBJECT, MapMarkerIds.HIGHLIGHT_OBJECT -> {
                val obj = catalog.objects.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                showObject(obj)
            }

            MapMarkerIds.WILD -> showWildPokemon(value)
        }
    }

    private fun showObject(obj: MapObject) {
        val game = loaded.value?.game ?: return
        when (obj.kind) {
            MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> {
                val detail = MapDetail.Item(obj)
                _state.update { it.copy(detail = detail, zoneListOpen = false) }
                val itemId = obj.itemId ?: return
                viewModelScope.launch {
                    val details = getObjectDetails.item(game, itemId)
                    _state.update { if (it.detail == detail) it.copy(detail = detail.copy(details = details)) else it }
                }
            }

            else -> {
                val detail = MapDetail.Character(obj)
                _state.update { it.copy(detail = detail, zoneListOpen = false) }
                viewModelScope.launch {
                    val isTrainer = obj.kind == MapObjectKind.TRAINER
                    val party = if (isTrainer) getObjectDetails.trainerParty(game, obj.id) else emptyList()
                    val ready = detail.copy(loading = false, party = party, offers = getObjectDetails.offers(obj.id))
                    _state.update { if (it.detail == detail) it.copy(detail = ready) else it }
                }
            }
        }
    }

    // --- Surlignage ----------------------------------------------------------------------------

    /**
     * Surligne les lieux d'un Pokémon et recentre la carte du monde sur eux (`move`). Un Pokémon qu'on n'obtient
     * qu'auprès d'un personnage (don, échange) : on entre directement chez lui.
     */
    private suspend fun highlight(pokemonId: Int, name: String, move: Boolean = true) {
        val gameMaps = loaded.value ?: return
        val catalog = gameMaps.catalog
        val world = catalog.world ?: return
        val found = getPokemonMaps(gameMaps.game, catalog, pokemonId)
        highlightedMaps = found.maps
        highlightedObjects = found.givers.map { it.id }.toSet()
        if (highlightedMaps.isEmpty()) {
            _state.update { it.copy(highlight = null, notFound = name) }
        } else {
            val giverMaps = found.givers.map { it.mapId }.toSet()
            val places = found.givers.mapNotNull { giver ->
                catalog.maps[giver.mapId]?.let { MapPlace(it.id, it.name, giver.x, giver.y) }
            } + highlightedMaps.filter { it !in giverMaps }.mapNotNull { catalog.maps[it] }.sortedBy { it.id }
                .map { MapPlace(it.id, it.name) }
            _state.update { it.copy(highlight = MapHighlight(pokemonId, name, places), detail = null) }
        }
        if (!move) {
            refreshOverlays()
            return
        }
        if (found.onlyFromGivers) {
            focusObject(found.givers.first())
            return
        }
        if (_state.value.map?.id == world.id) {
            clearZone()
        } else {
            show(world.id, null, null, null)
        }
        focusOnHighlight(catalog, world)
    }

    /** Ouvre la carte d'un objet ou d'un personnage (son bâtiment), centrée sur lui, avec sa fiche. */
    private fun focusObject(obj: MapObject) {
        _state.update { it.copy(detail = null, zoneListOpen = false) }
        open(obj.mapId, obj.x, obj.y)
        focusedObjectId = obj.id
        showObject(obj)
        refreshOverlays()
    }

    // --- Changement de version -----------------------------------------------------------------

    /** Carte affichée, lieu sélectionné, centre de l'écran et zoom, par identifiants (communs aux jeux). */
    private data class Position(
        val mapIdentifier: String,
        val zoneIdentifier: String?,
        val x: Double,
        val y: Double,
        val scale: Double
    )

    private fun currentPosition(): Position? {
        val catalog = catalog ?: return null
        val map = _state.value.map ?: return null
        val mapState = _state.value.mapState ?: return null
        val zone = _state.value.zone?.let { catalog.maps[it.mapId]?.identifier }
        return Position(map.identifier, zone, mapState.centroidX, mapState.centroidY, mapState.scale)
    }

    /** Reste à la même position dans le nouveau jeu ; false si la carte n'y existe pas. */
    private fun stay(catalog: MapCatalog, position: Position, sameMaps: Boolean): Boolean {
        val map = catalog.maps.values.firstOrNull { it.identifier == position.mapIdentifier && it.isDisplayable }
            ?: return false
        // Mêmes cartes (Rouge ↔ Bleu) : la carte affichée reste, seules les rencontres changent.
        if (!sameMaps || _state.value.map?.id != map.id) {
            show(map.id, position.x, position.y, position.scale)
        }
        val zone = position.zoneIdentifier?.let(catalog::mapByIdentifier)
            ?.takeIf { catalog.displayedMapOf(it.id)?.id == map.id }
        if (zone != null) selectZone(catalog, zone.id) else clearZone()
        return true
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

    /** Redessine marqueurs, contour du lieu sélectionné et surlignage de la carte affichée. */
    private val overlayRenderer = MapOverlayRenderer()

    private fun refreshOverlays() {
        val catalog = catalog ?: return
        val current = _state.value
        val map = current.map ?: return
        val mapState = current.mapState ?: return
        overlayRenderer.render(
            MapRenderState(
                catalog = catalog,
                map = map,
                mapState = mapState,
                layers = current.layers,
                animated = current.animatedSprites,
                zone = current.zone?.let { catalog.maps[it.mapId] },
                wildMarkers = wildMarkers,
                focusedObjectId = focusedObjectId,
                highlightedPokemonId = current.highlight?.pokemonId,
                highlightedMaps = highlightedMaps,
                highlightedObjects = highlightedObjects,
                worldEntrances = worldEntrances,
                objectScales = objectScales
            )
        )
    }

    override fun onCleared() {
        _state.value.mapState?.shutdown()
    }

    private companion object {
        const val START_REGION = "pallet-town"
        const val WORLD_SCALE = 2.0
        const val FOCUS_SCALE = 4.0
        const val ZONE_FOCUS_MIN_SCALE = 3.0
        const val MAX_SCALE = 12.0
        const val CENTER = 0.5
        const val ENTRANCE_MARGIN = 48
        const val WARP_TOUCH_RADIUS_DP = 24f
        const val WARP_TOUCH_MIN_SCALE = 1.0
        const val SHUTDOWN_DELAY_MS = 600L
        val MAP_BACKGROUND = Color(0xFF202028)
    }
}
