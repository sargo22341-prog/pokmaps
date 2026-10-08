package org.opensources.pokmaps.ui.map

import androidx.compose.ui.geometry.Offset
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import org.opensources.pokmaps.domain.usecase.GetPokemonMapsUseCase
import org.opensources.pokmaps.domain.usecase.MapLayersUseCase
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObserveMapCatalogUseCase
import ovh.plrapps.mapcompose.api.BoundingBox
import ovh.plrapps.mapcompose.api.centroidX
import ovh.plrapps.mapcompose.api.centroidY
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.api.scrollTo

/**
 * Cartes du jeu choisi, affichées avec MapCompose : cartes du monde par région et cartes intérieures,
 * lieux cliquables (leur contenu s'affiche sur la carte), calques et surlignage des lieux d'un Pokémon.
 *
 * Les déplacements entre cartes sont confiés à [MapNavigation], le lieu sélectionné et les fiches à
 * [MapSelection] ; le ViewModel relie les sources de données, les demandes des autres écrans et le surlignage.
 */
@HiltViewModel
class MapViewModel @Inject constructor(
    private val observeCatalog: ObserveMapCatalogUseCase,
    getMapEncounters: GetMapEncountersUseCase,
    private val getPokemonMaps: GetPokemonMapsUseCase,
    getObjectDetails: GetMapObjectDetailsUseCase,
    private val mapRequests: MapRequests,
    private val mapLayers: MapLayersUseCase,
    private val observeCollection: ObserveCollectionUseCase,
    getMapTiles: GetMapTilesUseCase
) : ViewModel() {
    private val session = MapSession(viewModelScope)
    private val selection = MapSelection(session, getMapEncounters, getObjectDetails)
    private val navigation = MapNavigation(session, selection, getMapTiles)

    val state: StateFlow<MapUiState> = session.state

    /** L'écran de la carte a déjà été affiché une fois (voir [onScreenShown]). */
    private var screenShown = false

    /**
     * L'écran de la carte est affiché. Changements de jeu et demandes des autres écrans attendent qu'il le soit :
     * une carte MapCompose créée ou déplacée pendant qu'il est caché serait recréée à son retour
     * ([onScreenShown]) à l'ancienne position, et le recentrage (« Voir sur la carte ») perdu.
     */
    private val screenVisible = MutableStateFlow(false)

    init {
        viewModelScope.launch { followCatalog() }
        viewModelScope.launch { followRequests() }
        viewModelScope.launch { followLayers() }
        viewModelScope.launch {
            observeCollection().collect { collection -> session.update { it.copy(caught = collection.caught) } }
        }
    }

    fun onAction(action: MapAction) {
        when (action) {
            MapAction.Back -> navigation.back()

            is MapAction.OpenPlace -> navigation.openPlace(action.place)

            is MapAction.SelectWorld -> navigation.selectWorld(action.mapId)

            is MapAction.ToggleTime -> selection.toggleTime(action.time)

            is MapAction.SelectFloor -> navigation.selectFloor(action.mapId)

            is MapAction.ToggleLayer -> toggleLayer(action.layer)

            MapAction.ClearHighlight -> clearHighlight()

            MapAction.ClearZone -> selection.clearZone()

            MapAction.OpenZoneList -> session.update { it.copy(zoneListOpen = true, detail = null) }

            MapAction.CloseZoneList -> session.update { it.copy(zoneListOpen = false) }

            MapAction.DismissDetail -> selection.dismissDetail()

            is MapAction.FocusObject -> session.loaded.value?.catalog?.objectsById?.get(action.objectId)
                ?.let(navigation::focusObject)

            MapAction.MessageShown -> session.update { it.copy(message = null) }
        }
    }

    /**
     * L'écran de la carte revient (après le Pokédex, une fiche…) : la carte MapCompose, restée en mémoire alors
     * que son affichage était détruit, est recréée à la même position, avec le même lieu sélectionné. Sans cela,
     * ses gestes gardent l'état de l'ancien affichage et les touches ne sélectionnent plus d'autre lieu.
     */
    fun onScreenShown() {
        if (screenShown) recreateMap()
        screenShown = true
        screenVisible.value = true
    }

    /** L'écran de la carte est quitté (Pokédex, fiche…). */
    fun onScreenHidden() {
        screenVisible.value = false
    }

    private fun recreateMap() {
        val current = session.current
        val map = current.map ?: return
        val mapState = current.mapState ?: return
        val overlays = session.overlays
        navigation.show(map.id, mapState.centroidX, mapState.centroidY, mapState.scale)
        session.updateOverlays {
            it.copy(wildMarkers = overlays.wildMarkers, focusedObjectId = overlays.focusedObjectId)
        }
        session.update { it.copy(zone = current.zone, detail = current.detail, zoneListOpen = current.zoneListOpen) }
        session.refreshOverlays()
    }

    private suspend fun followCatalog() {
        observeCatalog().catch { session.update { it.copy(failed = true) } }.collect { gameMaps ->
            awaitScreen()
            val previous = session.loaded.value
            // Changement de version : on reste là où on est si la carte existe aussi dans le nouveau jeu
            // (Rouge et Bleu partagent leurs cartes, Jaune a presque toutes les mêmes), pour comparer.
            val position = navigation.currentPosition()
            session.setLoaded(gameMaps)
            session.updateOverlays { it.copy(worldEntrances = gameMaps.catalog.worldEntrances()) }
            val sameMaps = previous?.catalog === gameMaps.catalog
            if (!sameMaps) navigation.forgetScales()
            session.update {
                it.copy(
                    game = gameMaps.game,
                    detail = null,
                    zoneListOpen = false,
                    failed = false,
                    worlds = gameMaps.catalog.worlds.map { world -> MapPlace(world.id, world.name) }
                )
            }
            val stayed = position != null && navigation.stay(gameMaps.catalog, position, sameMaps)
            val current = session.current.highlight
            when {
                current != null -> highlight(current.pokemonId, current.name, move = !stayed)
                !stayed -> gameMaps.catalog.defaultWorld?.let { navigation.open(it.id) }
            }
        }
    }

    /** Demandes venues des autres écrans (« Voir sur la carte »), traitées une fois le catalogue lu. */
    private suspend fun followRequests() {
        mapRequests.pending.filterNotNull().collect { request ->
            awaitScreen()
            val gameMaps = withTimeoutOrNull(CATALOG_WAIT_MS) { session.loaded.filterNotNull().first() }
            if (gameMaps == null) {
                session.update { it.copy(failed = true) }
            } else {
                handle(request, gameMaps)
            }
            mapRequests.consume(request)
        }
    }

    private suspend fun awaitScreen() {
        screenVisible.first { it }
    }

    private suspend fun handle(request: MapRequest, gameMaps: GameMaps) {
        val catalog = gameMaps.catalog
        when (request) {
            is MapRequest.HighlightPokemon -> highlight(request.pokemonId, request.name)

            is MapRequest.OpenPlace -> catalog.mapByIdentifier(request.mapIdentifier)?.let { map ->
                session.update { it.copy(detail = null, zoneListOpen = false) }
                navigation.open(map.id)
            }

            is MapRequest.FocusObject -> catalog.objectsById[request.objectId]?.let(navigation::focusObject)
        }
    }

    private suspend fun followLayers() {
        mapLayers.layers.collect { layers ->
            if (layers == session.current.layers) return@collect
            session.update { it.copy(layers = layers) }
            session.refreshOverlays()
        }
    }

    private fun toggleLayer(layer: MapLayer) {
        val layers = session.current.layers.let { if (layer in it) it - layer else it + layer }
        session.update { it.copy(layers = layers) }
        session.refreshOverlays()
        viewModelScope.launch { mapLayers.set(layers) }
    }

    private fun clearHighlight() {
        session.updateOverlays { it.copy(highlightedMaps = emptySet(), highlightedObjects = emptySet()) }
        session.update { it.copy(highlight = null) }
        session.refreshOverlays()
    }

    // --- Surlignage ----------------------------------------------------------------------------

    /**
     * Surligne les lieux d'un Pokémon et recentre la carte du monde sur eux (`move`). Un Pokémon qu'on n'obtient
     * qu'auprès d'un personnage (don, échange) : on entre directement chez lui.
     */
    private suspend fun highlight(pokemonId: Int, name: String, move: Boolean = true) {
        val gameMaps = session.loaded.value ?: return
        val catalog = gameMaps.catalog
        val found = session.attempt { getPokemonMaps(gameMaps.game, catalog, pokemonId) }.getOrElse {
            session.update { it.copy(highlight = null, message = MapMessage.HighlightFailed(name)) }
            return
        }
        session.updateOverlays {
            it.copy(highlightedMaps = found.maps, highlightedObjects = found.givers.map { giver -> giver.id }.toSet())
        }
        if (found.maps.isEmpty()) {
            session.update { it.copy(highlight = null, message = MapMessage.NotFound(name)) }
        } else {
            val highlight = MapHighlight(pokemonId, name, highlightedPlaces(catalog, found.maps, found.givers))
            session.update { it.copy(highlight = highlight, detail = null) }
        }
        if (!move) {
            session.refreshOverlays()
            return
        }
        val foundWorlds = found.maps.mapNotNull { catalog.worldOf(it) }.distinctBy { it.id }
        val world = foundWorlds.firstOrNull { it.id == session.current.map?.id }
            ?: foundWorlds.firstOrNull() ?: catalog.defaultWorld ?: return
        if (found.onlyFromGivers) {
            navigation.focusObject(found.givers.first())
            return
        }
        if (session.current.map?.id == world.id) {
            selection.clearZone()
        } else {
            navigation.show(world.id, null, null, null)
        }
        focusOnHighlight(catalog, world)
    }

    /** Personnages qui donnent le Pokémon (chez eux), puis les autres lieux où il se trouve. */
    private fun highlightedPlaces(catalog: MapCatalog, maps: Set<Int>, givers: List<MapObject>): List<MapPlace> {
        val giverMaps = givers.map { it.mapId }.toSet()
        val atGivers = givers.mapNotNull { giver ->
            catalog.maps[giver.mapId]?.let { MapPlace(it.id, it.name, giver.x, giver.y) }
        }
        return atGivers + maps.filter { it !in giverMaps }.mapNotNull { catalog.maps[it] }.sortedBy { it.id }
            .map { MapPlace(it.id, it.name) }
    }

    /** Recentre la carte du monde sur les villes, routes et entrées surlignées. */
    private suspend fun focusOnHighlight(catalog: MapCatalog, world: MapInfo) {
        val mapState = session.current.mapState ?: return
        val overlays = session.overlays
        val boxes = overlays.highlightedMaps.mapNotNull { catalog.maps[it] }.mapNotNull { map ->
            if (map.parentId == world.id) {
                Box(map.x, map.y, map.x + map.width, map.y + map.height)
            } else if (catalog.worldOf(map.id)?.id == world.id) {
                overlays.worldEntrances[map.id]?.let {
                    Box(it.x - ENTRANCE_MARGIN, it.y - ENTRANCE_MARGIN, it.x + ENTRANCE_MARGIN, it.y + ENTRANCE_MARGIN)
                } ?: catalog.maps[map.originMapId]?.let { origin ->
                    Box(origin.x, origin.y, origin.x + origin.width, origin.y + origin.height)
                }
            } else {
                null
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

    override fun onCleared() {
        session.current.mapState?.shutdown()
    }

    private companion object {
        const val ENTRANCE_MARGIN = 48
        const val CATALOG_WAIT_MS = 30_000L
    }
}
