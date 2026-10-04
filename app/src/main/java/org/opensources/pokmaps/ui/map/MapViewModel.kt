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
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapFloor
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.SpotKind
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.map.WildPlacement
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterGroup
import org.opensources.pokmaps.domain.model.Game
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
import org.opensources.pokmaps.ui.common.PixelArt
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

/** Lieu vers lequel on peut aller : carte (ou ville, route) et point d'arrivée, en pixels de la carte affichée. */
data class MapPlace(val mapId: Int, val name: String, val x: Int? = null, val y: Int? = null)

/** Façon de rencontrer un Pokémon sauvage, qui décide où le dessiner sur la carte. */
enum class WildMethod {
    /** Herbes hautes, ou sol des grottes et bâtiments. */
    WALK,
    SURF,
    FISHING;

    companion object {
        fun from(method: String): WildMethod? = when (method) {
            "walk" -> WALK
            "surf" -> SURF
            "old-rod", "good-rod", "super-rod" -> FISHING
            else -> null
        }
    }
}

/** Pokémon sauvage dessiné sur la carte, à un emplacement de son terrain (en pixels de la carte affichée). */
data class WildMarker(
    val pokemonId: Int,
    val name: String,
    val method: WildMethod,
    val x: Int,
    val y: Int,
    val scale: Float = 1f
)

/**
 * Lieu sélectionné (ville, route ou carte intérieure) : son contenu est dessiné sur la carte
 * (Pokémon sauvages, objets, personnages), la liste détaillée s'ouvre à la demande.
 */
data class MapZone(
    val mapId: Int,
    val name: String,
    val places: List<MapPlace>,
    val loading: Boolean = true,
    val encounters: List<Encounter> = emptyList()
) {
    val groups: List<EncounterGroup> get() = encounters.groupByMethod()

    /** Pokémon sauvages du lieu (herbes, grottes, surf, pêche). */
    val wildIds: Set<Int> get() = encounters.filter { WildMethod.from(it.method) != null }.map { it.pokemonId }.toSet()
}

/** Élément touché sur la carte, détaillé dans la carte en bas d'écran. */
sealed interface MapDetail {
    data class WildPokemon(val pokemonId: Int, val name: String, val encounters: List<EncounterGroup>) : MapDetail

    data class Item(val obj: MapObject, val details: ItemDetails? = null) : MapDetail

    /** Dresseur, personnage ou Pokémon fixe ; `loading` tant que l'équipe et les offres ne sont pas lues. */
    data class Character(
        val obj: MapObject,
        val loading: Boolean = true,
        val party: List<TrainerPokemon> = emptyList(),
        val offers: List<NpcOffer> = emptyList()
    ) : MapDetail
}

/** Mode « surlignage » : lieux d'un Pokémon dans la version choisie. */
data class MapHighlight(val pokemonId: Int, val name: String, val places: List<MapPlace>)

data class MapUiState(
    val game: Game? = null,
    val map: GameMap? = null,
    val mapState: MapState? = null,
    /** Niveau du dessus (bâtiment, ville ou route qui contient la carte intérieure), pour le bouton retour. */
    val parent: MapPlace? = null,
    /** Étages du bâtiment ou de la grotte affiché, de haut en bas (vide s'il n'a qu'un niveau). */
    val floors: List<MapFloor> = emptyList(),
    val layers: Set<MapLayer> = MapLayer.entries.toSet(),
    /** Pokémon capturés dans la version. */
    val caught: Set<Int> = emptySet(),
    val zone: MapZone? = null,
    val detail: MapDetail? = null,
    /** Liste détaillée du lieu sélectionné ouverte. */
    val zoneListOpen: Boolean = false,
    val highlight: MapHighlight? = null,
    /** Pokémon introuvable sur les cartes de la version (message à afficher une fois). */
    val notFound: String? = null
)

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

    /** Chemins (surlignage, contour du lieu) dessinés sur la carte affichée. */
    private val drawnPaths = mutableListOf<String>()

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
            addLazyLoader(LAZY_LOADER, padding = 64.dp)
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
        val zone = MapZone(zoneId, info.name, places(catalog, info))
        wildMarkers = emptyList()
        _state.update { it.copy(zone = zone, detail = null, zoneListOpen = false) }
        refreshOverlays()
        viewModelScope.launch {
            val encounters = getMapEncounters(game, catalog, zoneId)
            val ready = zone.copy(loading = false, encounters = encounters)
            if (_state.value.zone != zone) return@launch
            wildMarkers = wildMarkers(catalog, info, encounters)
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

    /** Lieux accessibles depuis une ville, une route ou une carte intérieure (bâtiments, grottes, étages, sorties). */
    private fun places(catalog: MapCatalog, zone: MapInfo): List<MapPlace> =
        catalog.accessibleFrom(zone.id).mapNotNull { warp ->
            val target = warp.targetMapId?.let { catalog.maps[it] } ?: return@mapNotNull null
            MapPlace(target.id, target.name, warp.targetX, warp.targetY)
        }

    /**
     * Dessine les Pokémon sauvages du lieu sur leur terrain : herbes (ou sol des grottes) en marchant, eau en surfant
     * ou en pêchant. Chacun apparaît au moins une fois (les plus fréquents parfois deux), à des emplacements bien
     * répartis sur le terrain ; sur un terrain étroit, ils sont rangés côte à côte, plus petits.
     */
    private fun wildMarkers(catalog: MapCatalog, zone: MapInfo, encounters: List<Encounter>): List<WildMarker> {
        val spots = catalog.spots[zone.id].orEmpty().groupBy { it.kind }
        // Objets, personnages et entrées gardent leur place : pas de Pokémon dessiné juste à côté.
        val displayed = catalog.displayedMapOf(zone.id)?.id ?: zone.id
        val obstacles = catalog.partsOf(displayed).flatMap { catalog.objects[it].orEmpty() }.map { it.x to it.y } +
            catalog.entrancesOf(displayed).map { it.x to it.y }
        val wild = encounters.mapNotNull { e -> WildMethod.from(e.method)?.let { it to e } }
        // Surf et pêche partagent l'eau : ils sont répartis ensemble pour ne pas se superposer.
        return wild.groupBy { (method, _) -> method == WildMethod.WALK }.flatMap { (walking, list) ->
            val terrain = if (walking) spots[SpotKind.GRASS] ?: spots[SpotKind.FLOOR] else spots[SpotKind.WATER]
            val species = list.groupBy { (method, e) -> method to e.pokemonId }.map { (key, group) ->
                val encounter = group.first().second
                WildMarker(encounter.pokemonId, encounter.pokemonName, key.first, 0, 0) to
                    group.sumOf { it.second.chance ?: 0.0 }
            }.sortedByDescending { it.second }
            WildPlacement.place(
                items = species.map { it.first },
                weights = species.map { it.second },
                spots = WildPlacement.awayFrom(terrain.orEmpty().map { it.x to it.y }, obstacles, species.size),
                fallback = zone.centerInDisplay(),
                seed = zone.id * 2 + if (walking) 0 else 1
            ).map { it.item.copy(x = it.x, y = it.y, scale = it.scale) }
        }
    }

    private fun MapInfo.centerInDisplay(): Pair<Int, Int> =
        if (parentId == null) width / 2 to height / 2 else x + width / 2 to y + height / 2

    private fun handleMarkerClick(id: String) {
        val catalog = catalog ?: return
        val parts = id.split(':')
        val prefix = parts[0]
        val value = parts.getOrNull(1)?.toIntOrNull() ?: return
        when (prefix) {
            WARP, HIGHLIGHT_WARP -> {
                val warp = catalog.warps.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                enter(catalog, warp)
            }

            OBJECT, HIGHLIGHT_OBJECT -> {
                val obj = catalog.objects.values.asSequence().flatten().firstOrNull { it.id == value } ?: return
                showObject(obj)
            }

            WILD -> showWildPokemon(value)
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
    private fun refreshOverlays() {
        val catalog = catalog ?: return
        val map = _state.value.map ?: return
        val mapState = _state.value.mapState ?: return
        val layers = _state.value.layers
        val zone = _state.value.zone?.let { catalog.maps[it.mapId] }
        mapState.removeAllMarkers()
        drawnPaths.forEach { mapState.removePath(it) }
        drawnPaths.clear()

        fun MapState.marker(
            id: String,
            x: Int,
            y: Int,
            lazy: Boolean = true,
            zIndex: Float = 0f,
            pokemon: Boolean = false,
            content: @Composable () -> Unit
        ) = addMarker(
            id,
            x.toDouble() / map.width,
            y.toDouble() / map.height,
            // Une icône de Pokémon est centrée sur son dessin (en bas de l'image), et ne se touche que sur lui.
            relativeOffset = if (pokemon) POKEMON_OFFSET else CENTERED,
            zIndex = zIndex,
            clickableAreaScale = if (pokemon) POKEMON_CLICK_SCALE else FULL_CLICK_SCALE,
            clickableAreaCenterOffset = if (pokemon) POKEMON_CLICK_CENTER else NO_OFFSET,
            renderingStrategy = if (lazy) RenderingStrategy.LazyLoading(LAZY_LOADER) else RenderingStrategy.Default,
            c = content
        )

        fun rectangle(id: String, part: MapInfo, color: Color, fillAlpha: Float) {
            val whole = part.parentId == null
            val left = if (whole) 0.0 else part.x.toDouble() / map.width
            val top = if (whole) 0.0 else part.y.toDouble() / map.height
            val right = if (whole) 1.0 else min(1.0, (part.x + part.width).toDouble() / map.width)
            val bottom = if (whole) 1.0 else min(1.0, (part.y + part.height).toDouble() / map.height)
            mapState.addPath(id, width = 3.dp, color = color, fillColor = color.copy(alpha = fillAlpha)) {
                addPoints(listOf(left to top, right to top, right to bottom, left to bottom, left to top))
            }
            drawnPaths += id
        }

        // Parties de la carte dont le contenu est affiché à tout zoom : le lieu sélectionné. Ailleurs, les marqueurs
        // des calques n'apparaissent qu'en zoomant.
        val zoneParts = when {
            zone == null -> emptySet()
            zone.parentId == null -> catalog.partsOf(zone.id).toSet()
            else -> setOf(zone.id)
        }
        if (zone != null && zone.parentId != null) rectangle("$ZONE_PATH:${zone.id}", zone, ZONE_COLOR, 0f)

        val entrances = catalog.entrancesOf(map.id)
        if (MapLayer.WARPS in layers) {
            entrances.forEach { warp ->
                val always = warp.mapId in zoneParts
                mapState.marker("$WARP:${warp.id}", warp.x, warp.y, lazy = !always, zIndex = 2f) {
                    WarpMarker(mapState, alwaysVisible = always)
                }
            }
        }
        val objects = catalog.partsOf(map.id).flatMap { catalog.objects[it].orEmpty() }
        objects.filter { MapLayer.of(it.kind) in layers }.forEach { obj ->
            val inZone = obj.mapId in zoneParts
            val pokemon = obj.kind == MapObjectKind.POKEMON && obj.pokemonId != null
            mapState.marker("$OBJECT:${obj.id}", obj.x, obj.y, lazy = !inZone, zIndex = 1f, pokemon = pokemon) {
                ObjectMarker(mapState, obj, catalog.versionGroupIdentifier, alwaysVisible = inZone)
            }
        }
        if (MapLayer.WILD_POKEMON in layers) {
            wildMarkers.forEachIndexed { index, wild ->
                mapState.marker(
                    "$WILD:${wild.pokemonId}:$index",
                    wild.x,
                    wild.y,
                    lazy = false,
                    zIndex = 1f,
                    pokemon = true
                ) {
                    WildPokemonMarker(mapState, wild)
                }
            }
        }

        focusedObjectId?.let { catalog.objectsById[it] }?.takeIf { it.mapId in catalog.partsOf(map.id) }?.let { obj ->
            mapState.marker("$HIGHLIGHT_OBJECT:${obj.id}", obj.x, obj.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }

        val pokemonId = _state.value.highlight?.pokemonId ?: return
        // Villes et routes surlignées sur la carte du monde, ou toute la carte intérieure.
        catalog.partsOf(map.id).filter { it in highlightedMaps }.mapNotNull { catalog.maps[it] }.forEach { part ->
            rectangle("$HIGHLIGHT_PATH:${part.id}", part, HIGHLIGHT_COLOR, 0.25f)
        }
        // Entrées menant aux cartes intérieures surlignées.
        val highlightedEntrances = if (map.identifier == GameMap.WORLD) {
            highlightedMaps.mapNotNull { worldEntrances[it] }
        } else {
            entrances.filter { it.targetMapId in highlightedMaps }
        }
        highlightedEntrances.distinctBy { it.id }.forEach { warp ->
            mapState.marker("$HIGHLIGHT_WARP:${warp.id}", warp.x, warp.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }
        objects.filter {
            ((it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId) || it.id in highlightedObjects) &&
                it.id != focusedObjectId
        }.forEach { obj ->
            mapState.marker("$HIGHLIGHT_OBJECT:${obj.id}", obj.x, obj.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }
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
        const val LAZY_LOADER = "lazy"
        const val WARP = "w"
        const val OBJECT = "o"
        const val WILD = "p"
        const val HIGHLIGHT_WARP = "hw"
        const val HIGHLIGHT_OBJECT = "ho"
        const val HIGHLIGHT_PATH = "hp"
        const val ZONE_PATH = "zp"
        const val SHUTDOWN_DELAY_MS = 600L
        val CENTERED = Offset(-0.5f, -0.5f)
        val POKEMON_OFFSET = Offset(-0.5f, -PixelArt.POKEMON_CENTER_Y)
        val FULL_CLICK_SCALE = Offset(1f, 1f)
        val NO_OFFSET = Offset(0f, 0f)
        val POKEMON_CLICK_SCALE = Offset(PixelArt.POKEMON_CONTENT_WIDTH, 0.6f)
        val POKEMON_CLICK_CENTER = Offset(0f, PixelArt.POKEMON_CENTER_Y - 0.5f)
        val MAP_BACKGROUND = Color(0xFF202028)
        val ZONE_COLOR = Color(0xFFFFFFFF)
    }
}
