package org.opensources.pokmaps.ui.move

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
import org.opensources.pokmaps.domain.usecase.MovePage
import org.opensources.pokmaps.domain.usecase.ObserveMoveUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

/** Fiche d'une attaque : `page.details` est null si le jeu choisi ne la connaît pas (ce n'est pas une erreur). */
data class MoveUiState(val loading: Boolean = true, val page: MovePage? = null, val failed: Boolean = false)

/** Fiche d'une attaque dans le jeu choisi. */
@HiltViewModel
class MoveViewModel @Inject constructor(savedStateHandle: SavedStateHandle, observeMove: ObserveMoveUseCase) :
    ViewModel() {
    private val moveId: Int = checkNotNull(savedStateHandle[MOVE_ID])

    val state: StateFlow<MoveUiState> = observeMove(moveId)
        .map { MoveUiState(loading = false, page = it) }
        .catch { emit(MoveUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), MoveUiState())

    companion object {
        const val MOVE_ID = "moveId"
    }
}
