package org.opensources.pokmaps.ui.game

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.usecase.ObserveGamesUseCase
import org.opensources.pokmaps.domain.usecase.ObserveSelectedGameUseCase
import org.opensources.pokmaps.domain.usecase.SelectGameUseCase

data class GameUiState(val games: List<Game> = emptyList(), val selected: Game? = null)

/** Sélecteur de jeu global, affiché dans la barre du haut. */
@HiltViewModel
class GameViewModel @Inject constructor(
    observeGames: ObserveGamesUseCase,
    observeSelectedGame: ObserveSelectedGameUseCase,
    private val selectGame: SelectGameUseCase
) : ViewModel() {
    val state: StateFlow<GameUiState> =
        combine(observeGames(), observeSelectedGame()) { games, selected -> GameUiState(games, selected) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), GameUiState())

    fun select(game: Game) {
        viewModelScope.launch { selectGame(game) }
    }
}

const val STOP_TIMEOUT_MS = 5_000L
