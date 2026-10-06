package org.opensources.pokmaps.ui.item

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
import org.opensources.pokmaps.domain.usecase.ItemPage
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveItemPageUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class ItemUiState(val loading: Boolean = true, val page: ItemPage? = null, val failed: Boolean = false)

/** Intentions de la fiche d'un objet. */
sealed interface ItemAction {
    /** Montre sur la carte un exemplaire de l'objet ou le personnage qui le vend ou le donne. */
    data class ShowOnMap(val objectId: Int) : ItemAction
}

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
        .catch { emit(ItemUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), ItemUiState())

    fun onAction(action: ItemAction) {
        when (action) {
            // La carte montre l'objet ou le personnage, dans son bâtiment.
            is ItemAction.ShowOnMap -> mapRequests.send(MapRequest.FocusObject(action.objectId))
        }
    }

    companion object {
        const val ITEM = "item"
    }
}
