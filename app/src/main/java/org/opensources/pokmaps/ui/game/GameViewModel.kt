package org.opensources.pokmaps.ui.game

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.usecase.ObserveGamesUseCase
import org.opensources.pokmaps.domain.usecase.ObserveSelectedGameUseCase
import org.opensources.pokmaps.domain.usecase.SelectGameUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

/** Jeux proposés et jeu choisi ; `failed` si la liste n'a pas pu être lue. */
data class GameUiState(
    val loading: Boolean = true,
    val games: List<Game> = emptyList(),
    val selected: Game? = null,
    val failed: Boolean = false
) {
    /** Jeux regroupés par génération, dans l'ordre des jeux. */
    val byGeneration: List<Pair<Int, List<Game>>> get() = games.groupBy { it.generationId }.toList()
}

/** Intentions de l'écran de choix du jeu. */
sealed interface GameAction {
    data class Select(val game: Game) : GameAction
}

/** Jeu choisi, mémorisé et appliqué à toute l'application (écran de choix du jeu, titre de la barre du haut). */
@HiltViewModel
class GameViewModel @Inject constructor(
    observeGames: ObserveGamesUseCase,
    observeSelectedGame: ObserveSelectedGameUseCase,
    private val selectGame: SelectGameUseCase
) : ViewModel() {
    // Sans aucun jeu, le jeu choisi n'est jamais émis : on part donc d'« aucun jeu choisi ».
    private val selected: Flow<Game?> = observeSelectedGame().map<Game, Game?> { it }.onStart { emit(null) }

    val state: StateFlow<GameUiState> =
        combine(observeGames(), selected) { games, selected ->
            GameUiState(loading = false, games = games, selected = selected)
        }.catch { emit(GameUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), GameUiState())

    fun onAction(action: GameAction) {
        when (action) {
            is GameAction.Select -> viewModelScope.launch { selectGame(action.game) }
        }
    }
}
