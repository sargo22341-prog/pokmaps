package org.opensources.pokmaps.ui.pokemon

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.CatchRate
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokemonUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

/** PV restants du Pokémon sauvage, en fraction de ses PV max (0 = 1 PV). */
enum class HpChoice(val fraction: Double) {
    FULL(1.0),
    HALF(0.5),
    QUARTER(0.25),
    ONE(0.0)
}

data class CatchInput(
    val level: Int? = null,
    val hp: HpChoice = HpChoice.FULL,
    val status: CatchStatus = CatchStatus.NONE
)

data class CatchUiState(
    val level: Int,
    val hp: HpChoice,
    val status: CatchStatus,
    val probabilities: List<Pair<Ball, Double>>,
    val best: Ball?
)

data class PokemonUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val game: Game? = null,
    val details: PokemonDetails? = null,
    /** Calcul de capture, seulement pour la 1re génération (formule propre à ces jeux). */
    val catch: CatchUiState? = null,
    /** Capturé dans la version choisie. */
    val caught: Boolean = false,
    val favorite: Boolean = false
)

@HiltViewModel
class PokemonViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observePokemon: ObservePokemonUseCase,
    observeCollection: ObserveCollectionUseCase,
    private val updateCollection: UpdateCollectionUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val pokemonId: Int = checkNotNull(savedStateHandle[POKEMON_ID])
    private val catchInput = MutableStateFlow(CatchInput())

    val state: StateFlow<PokemonUiState> =
        combine(observePokemon(pokemonId), observeCollection(), catchInput) { page, collection, input ->
            PokemonUiState(
                loading = false,
                game = page.game,
                details = page.details,
                catch = page.details?.takeIf { page.game.generationId == 1 }?.let { catchState(page.game, it, input) },
                caught = collection.game == page.game && pokemonId in collection.caught,
                favorite = pokemonId in collection.favorites
            )
        }.catch { emit(PokemonUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PokemonUiState())

    fun setCatchLevel(level: Int) = catchInput.update { it.copy(level = level.coerceIn(1, MAX_LEVEL)) }

    fun setCatchHp(hp: HpChoice) = catchInput.update { it.copy(hp = hp) }

    fun setCatchStatus(status: CatchStatus) = catchInput.update { it.copy(status = status) }

    fun toggleCaught() {
        val current = state.value
        val game = current.game ?: return
        viewModelScope.launch { updateCollection.setCaught(game, pokemonId, !current.caught) }
    }

    fun toggleFavorite() {
        val favorite = state.value.favorite
        viewModelScope.launch { updateCollection.setFavorite(pokemonId, !favorite) }
    }

    /** Demande à la carte de surligner les lieux du Pokémon. */
    fun showOnMap() {
        val details = state.value.details ?: return
        mapRequests.send(MapRequest.HighlightPokemon(details.id, details.name))
    }

    private fun catchState(game: Game, details: PokemonDetails, input: CatchInput): CatchUiState {
        // Niveau par défaut : le plus bas auquel on le rencontre dans la version.
        val level = input.level
            ?: details.encounters.filter { it.versionId == game.versionId && !it.isTrade }.minOfOrNull { it.minLevel }
            ?: DEFAULT_LEVEL
        val baseHp = details.stats.firstOrNull { it.identifier == HP }?.value ?: 0
        val maxHp = CatchRate.maxHp(baseHp, level)
        val currentHp = CatchRate.currentHp(maxHp, input.hp.fraction)
        val probabilities = BALLS.associateWith {
            CatchRate.probability(it, details.captureRate, maxHp, currentHp, input.status)
        }
        return CatchUiState(level, input.hp, input.status, probabilities.toList(), CatchRate.bestBall(probabilities))
    }

    companion object {
        const val POKEMON_ID = "pokemonId"
        private const val HP = "hp"
        private const val DEFAULT_LEVEL = 30
        const val MAX_LEVEL = 100
        private val BALLS = listOf(Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.MASTER)
    }
}
