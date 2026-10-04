package org.opensources.pokmaps.ui.character

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.usecase.CharacterPage
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCharacterPageUseCase
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class CharacterUiState(val loading: Boolean = true, val page: CharacterPage? = null)

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
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), CharacterUiState())

    fun showOnMap() = mapRequests.send(MapRequest.FocusObject(objectId))

    companion object {
        const val CHARACTER = "character"
    }
}
