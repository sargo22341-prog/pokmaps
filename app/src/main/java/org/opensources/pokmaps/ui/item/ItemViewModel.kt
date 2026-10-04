package org.opensources.pokmaps.ui.item

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.usecase.ItemPage
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveItemPageUseCase
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class ItemUiState(val loading: Boolean = true, val page: ItemPage? = null)

/** Fiche d'un objet du jeu choisi. */
@HiltViewModel
class ItemViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observeItem: ObserveItemPageUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val identifier: String = checkNotNull(savedStateHandle[ITEM])

    val state: StateFlow<ItemUiState> = observeItem(identifier)
        .map { ItemUiState(loading = false, page = it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), ItemUiState())

    /** Demande à la carte de montrer l'objet ou le personnage (dans son bâtiment). */
    fun showOnMap(objectId: Int) = mapRequests.send(MapRequest.FocusObject(objectId))

    companion object {
        const val ITEM = "item"
    }
}
