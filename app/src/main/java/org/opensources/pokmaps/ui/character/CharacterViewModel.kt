package org.opensources.pokmaps.ui.character

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
import org.opensources.pokmaps.domain.usecase.CharacterPage
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCharacterPageUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class CharacterUiState(val loading: Boolean = true, val page: CharacterPage? = null, val failed: Boolean = false)

/** Intentions de la fiche d'un personnage. */
sealed interface CharacterAction {
    /** Montre le personnage sur la carte, dans son bâtiment. */
    data object ShowOnMap : CharacterAction

    /** Montre un autre personnage sur la carte (ex. le scientifique qui ranime le fossile donné). */
    data class ShowObject(val objectId: Int) : CharacterAction
}

/** Fiche d'un personnage ou d'un dresseur. */
@HiltViewModel
class CharacterViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observeCharacter: ObserveCharacterPageUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val objectId: Int = checkNotNull(savedStateHandle[CHARACTER])

    val state: StateFlow<CharacterUiState> = observeCharacter(objectId)
        .map { CharacterUiState(loading = false, page = it) }
        .catch { emit(CharacterUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), CharacterUiState())

    fun onAction(action: CharacterAction) {
        when (action) {
            CharacterAction.ShowOnMap -> mapRequests.send(MapRequest.FocusObject(objectId))
            is CharacterAction.ShowObject -> mapRequests.send(MapRequest.FocusObject(action.objectId))
        }
    }

    companion object {
        const val CHARACTER = "character"
    }
}
