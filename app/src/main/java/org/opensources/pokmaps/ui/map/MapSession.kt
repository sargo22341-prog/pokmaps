package org.opensources.pokmaps.ui.map

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.usecase.GameMaps

/** Ce qui est dessiné sur la carte en plus de ses calques : Pokémon du lieu, éléments mis en évidence. */
internal data class MapOverlays(
    /** Pokémon sauvages dessinés pour le lieu sélectionné. */
    val wildMarkers: List<WildMarker> = emptyList(),
    /** Objet ou personnage mis en évidence (ouvert depuis une fiche). */
    val focusedObjectId: Int? = null,
    /** Cartes où se trouve le Pokémon surligné, et personnages qui le donnent ou l'échangent. */
    val highlightedMaps: Set<Int> = emptySet(),
    val highlightedObjects: Set<Int> = emptySet(),
    /** Entrée sur la carte du monde de chaque carte intérieure. */
    val worldEntrances: Map<Int, MapWarp> = emptyMap(),
    /** Taille des objets, personnages et Pokémon fixes de la carte affichée, selon la place autour d'eux. */
    val objectScales: Map<Int, Float> = emptyMap()
)

/**
 * État de l'écran de la carte, partagé par [MapViewModel] et les classes qui l'aident ([MapNavigation],
 * [MapSelection]). Les coroutines sont lancées dans le scope du ViewModel et meurent avec lui.
 */
internal class MapSession(private val scope: CoroutineScope) {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()
    val current: MapUiState get() = _state.value

    private val _loaded = MutableStateFlow<GameMaps?>(null)

    /** Cartes du jeu choisi, null tant que le catalogue n'est pas lu. */
    val loaded: StateFlow<GameMaps?> = _loaded.asStateFlow()
    val catalog: MapCatalog? get() = _loaded.value?.catalog

    var overlays = MapOverlays()
        private set

    private val renderer = MapOverlayRenderer()

    fun update(transform: (MapUiState) -> MapUiState) = _state.update(transform)

    fun setLoaded(gameMaps: GameMaps) {
        _loaded.value = gameMaps
    }

    fun updateOverlays(transform: (MapOverlays) -> MapOverlays) {
        overlays = transform(overlays)
    }

    fun launch(block: suspend CoroutineScope.() -> Unit): Job = scope.launch(block = block)

    /** Exécute `block` : `CancellationException` est relancée, toute autre erreur devient un résultat en échec. */
    suspend fun <T> attempt(block: suspend () -> T): Result<T> = try {
        Result.success(block())
    } catch (error: CancellationException) {
        throw error
    } catch (error: Exception) {
        Result.failure(error)
    }

    /**
     * Charge une donnée en arrière-plan. Une erreur de lecture ou de traitement du résultat appelle `onFailure`,
     * qui marque l'élément concerné en échec.
     */
    fun <T> load(block: suspend () -> T, onFailure: () -> Unit, onSuccess: (T) -> Unit): Job = scope.launch {
        attempt { onSuccess(block()) }.onFailure { onFailure() }
    }

    /** Redessine marqueurs, contour du lieu sélectionné et surlignage de la carte affichée. */
    fun refreshOverlays() {
        val catalog = catalog ?: return
        val current = _state.value
        val map = current.map ?: return
        val mapState = current.mapState ?: return
        renderer.render(
            MapRenderState(
                catalog = catalog,
                map = map,
                mapState = mapState,
                layers = current.layers,
                zone = current.zone?.let { catalog.maps[it.mapId] },
                overlays = overlays,
                highlightedPokemonId = current.highlight?.pokemonId
            )
        )
    }
}
