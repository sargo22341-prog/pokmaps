package org.opensources.pokmaps.ui.pokedex

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.usecase.ObservePokedexUseCase
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class PokedexUiState(val loading: Boolean = true, val entries: List<PokedexEntry> = emptyList())

@HiltViewModel
class PokedexViewModel @Inject constructor(observePokedex: ObservePokedexUseCase) : ViewModel() {
    val state: StateFlow<PokedexUiState> =
        observePokedex()
            .map { PokedexUiState(loading = false, entries = it) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PokedexUiState())
}
