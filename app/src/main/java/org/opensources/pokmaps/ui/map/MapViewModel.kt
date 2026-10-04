package org.opensources.pokmaps.ui.map

import androidx.compose.ui.graphics.Color
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.usecase.ObserveWorldMapUseCase
import ovh.plrapps.mapcompose.api.addLayer
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.api.setMapBackground
import ovh.plrapps.mapcompose.ui.state.MapState

data class MapUiState(val map: GameMap? = null, val mapState: MapState? = null)

/** Carte du monde du jeu choisi, affichée avec MapCompose. */
@HiltViewModel
class MapViewModel @Inject constructor(observeWorldMap: ObserveWorldMapUseCase, private val tiles: MapTiles) :
    ViewModel() {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            observeWorldMap().collect { map ->
                _state.value.mapState?.shutdown()
                _state.value = MapUiState(map, map?.let(::createMapState))
            }
        }
    }

    private fun createMapState(map: GameMap): MapState {
        // Départ centré sur Bourg Palette, à la taille réelle du jeu.
        val start = map.regions.firstOrNull { it.identifier == START_REGION }
        val x = (start?.centerX ?: (map.width / 2)).toDouble() / map.width
        val y = (start?.centerY ?: (map.height / 2)).toDouble() / map.height
        return MapState(map.levelCount, map.width, map.height, GameMap.TILE_SIZE) {
            scroll(x, y)
            scale(START_SCALE)
            maxScale(MAX_SCALE)
            // Pixels nets en zoom avant ; lissage seulement quand la carte est réduite.
            bitmapFilteringEnabled { state -> state.scale < 1.0 }
        }.apply {
            addLayer(tiles.provider(map))
            setMapBackground(MAP_BACKGROUND)
        }
    }

    override fun onCleared() {
        _state.value.mapState?.shutdown()
    }

    private companion object {
        const val START_REGION = "pallet-town"
        const val START_SCALE = 2.0
        const val MAX_SCALE = 8.0
        val MAP_BACKGROUND = Color(0xFF202028)
    }
}
