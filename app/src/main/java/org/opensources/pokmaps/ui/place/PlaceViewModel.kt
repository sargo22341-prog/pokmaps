package org.opensources.pokmaps.ui.place

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObservePlacePageUseCase
import org.opensources.pokmaps.domain.usecase.PlacePage
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class PlaceUiState(val loading: Boolean = true, val page: PlacePage? = null, val failed: Boolean = false)

/** Fiche d'un lieu (ville, route ou carte intérieure) du jeu choisi. */
@HiltViewModel
class PlaceViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observePlace: ObservePlacePageUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val identifier: String = checkNotNull(savedStateHandle[PLACE])

    val state: StateFlow<PlaceUiState> = observePlace(identifier)
        .map { PlaceUiState(loading = false, page = it) }
        .catch { emit(PlaceUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PlaceUiState())

    fun showOnMap() = mapRequests.send(MapRequest.OpenPlace(identifier))

    fun showObjectOnMap(objectId: Int) = mapRequests.send(MapRequest.FocusObject(objectId))

    companion object {
        const val PLACE = "place"
    }
}
