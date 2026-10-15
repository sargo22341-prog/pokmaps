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
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Generation
import org.opensources.pokmaps.domain.pokedex.CaptureScope
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.BallContext
import org.opensources.pokmaps.domain.pokemon.CaptureGeneration
import org.opensources.pokmaps.domain.pokemon.CatchRate
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.Gen2CatchRate
import org.opensources.pokmaps.domain.pokemon.Gen3CatchRate
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.MoveTab
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.domain.pokemon.ShinyOdds
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokemonUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.common.CollectionWrites
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

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
    val status: CatchStatus = CatchStatus.NONE,
    val playerLevel: Int = 30,
    val fishing: Boolean = false,
    val sameSpeciesAndGender: Boolean = false,
    val underwater: Boolean = false,
    val elapsedTurns: Int = 0,
    val alreadyCaught: Boolean = false
)

data class CatchUiState(
    val level: Int,
    val hp: HpChoice,
    val status: CatchStatus,
    val probabilities: List<Pair<Ball, Double>>,
    val best: Ball?,
    val generation: CaptureGeneration = CaptureGeneration.GEN1,
    val playerLevel: Int = 30,
    val fishing: Boolean = false,
    val sameSpeciesAndGender: Boolean = false,
    val underwater: Boolean = false,
    val elapsedTurns: Int = 0,
    val alreadyCaught: Boolean = false,
    val blockedBalls: Set<Ball> = emptySet()
)

data class PokemonUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val writeFailed: Boolean = false,
    val game: Game? = null,
    val details: PokemonDetails? = null,
    /** Calcul de capture avec la formule de la génération du jeu. */
    val catch: CatchUiState? = null,
    /** Capturé, selon la portée des captures (le jeu choisi, sa génération ou tous les jeux). */
    val caught: Boolean = false,
    val captureScope: CaptureScope = CaptureScope.DEFAULT,
    val favorite: Boolean = false,
    /** Sprites en couleurs chromatiques (en-tête et ligne d'évolution), jamais dans un jeu sans chromatiques. */
    val shiny: Boolean = false
) {
    /** Une rencontre sur [shinyOdds] est chromatique dans le jeu, null si le jeu n'a pas de chromatiques. */
    val shinyOdds: Int? get() = game?.let { ShinyOdds.oneIn(it.generationId) }

    /**
     * Les onglets œuf et tuteur apparaissent seulement si le Pokémon a des attaques dans le jeu choisi.
     */
    val moveTabs: List<MoveTab>
        get() = MoveTab.entries.filter { tab ->
            when (tab) {
                MoveTab.LEVEL_UP, MoveTab.MACHINE -> true

                MoveTab.EGG, MoveTab.TUTOR ->
                    details?.moves(tab).orEmpty().isNotEmpty()
            }
        }

    /** Le jeu connaît cette mécanique (objets tenus, sexe, œufs, talents…). */
    fun has(feature: GenerationFeature): Boolean = game?.let { feature.existsIn(it.generationId) } == true

    val hasUnownForms: Boolean
        get() = details?.id == UnownForm.POKEMON_ID &&
            game?.let { UnownForm.available(it).isNotEmpty() } == true
}

/** Intentions de la fiche d'un Pokémon. */
sealed interface PokemonAction {
    /** Coche ou décoche « capturé » dans la version choisie. */
    data object ToggleCaught : PokemonAction

    data object ToggleFavorite : PokemonAction

    /** Montre le Pokémon et sa ligne d'évolution en chromatique, ou en couleurs normales. */
    data object ToggleShiny : PokemonAction

    /** Surligne sur la carte les lieux du Pokémon. */
    data object ShowOnMap : PokemonAction

    data class SetCatchLevel(val level: Int) : PokemonAction

    data class SetCatchHp(val hp: HpChoice) : PokemonAction

    data class SetCatchStatus(val status: CatchStatus) : PokemonAction

    data class SetPlayerLevel(val level: Int) : PokemonAction

    data object ToggleFishing : PokemonAction

    data object ToggleLoveBonus : PokemonAction

    data object ToggleUnderwater : PokemonAction

    data object ToggleAlreadyCaught : PokemonAction

    data class SetElapsedTurns(val turns: Int) : PokemonAction
}

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
    private val collectionWrites = CollectionWrites(viewModelScope)
    private val shiny = MutableStateFlow(false)

    val state: StateFlow<PokemonUiState> =
        combine(observePokemon(pokemonId), observeCollection(), catchInput, shiny, collectionWrites.failed) {
                page,
                collection,
                input,
                shiny,
                writeFailed
            ->
            PokemonUiState(
                loading = false,
                writeFailed = writeFailed,
                game = page.game,
                details = page.details,
                catch = page.details?.takeIf { CaptureGeneration.from(page.game.generationId) != null }
                    ?.let { catchState(page.game, it, input) },
                caught = collection.game == page.game && pokemonId in collection.caught,
                captureScope = collection.scope,
                favorite = pokemonId in collection.favorites,
                // Un jeu sans chromatiques montre toujours les couleurs normales.
                shiny = shiny && GenerationFeature.SHINY.existsIn(page.game.generationId)
            )
        }.catch { emit(PokemonUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PokemonUiState())

    fun onAction(action: PokemonAction) {
        when (action) {
            PokemonAction.ToggleCaught -> toggleCaught()

            PokemonAction.ToggleFavorite -> toggleFavorite()

            PokemonAction.ToggleShiny -> if (state.value.shinyOdds != null) shiny.update { !it }

            PokemonAction.ShowOnMap -> showOnMap()

            is PokemonAction.SetCatchLevel ->
                catchInput.update { it.copy(level = action.level.coerceIn(1, MAX_LEVEL)) }

            is PokemonAction.SetCatchHp -> catchInput.update { it.copy(hp = action.hp) }

            is PokemonAction.SetCatchStatus -> catchInput.update { it.copy(status = action.status) }

            is PokemonAction.SetPlayerLevel ->
                catchInput.update { it.copy(playerLevel = action.level.coerceIn(1, MAX_LEVEL)) }

            PokemonAction.ToggleUnderwater -> catchInput.update { it.copy(underwater = !it.underwater) }

            PokemonAction.ToggleAlreadyCaught -> catchInput.update { it.copy(alreadyCaught = !it.alreadyCaught) }

            is PokemonAction.SetElapsedTurns ->
                catchInput.update { it.copy(elapsedTurns = action.turns.coerceIn(0, 30)) }

            PokemonAction.ToggleFishing -> catchInput.update { it.copy(fishing = !it.fishing) }

            PokemonAction.ToggleLoveBonus ->
                catchInput.update { it.copy(sameSpeciesAndGender = !it.sameSpeciesAndGender) }
        }
    }

    private fun toggleCaught() {
        val current = state.value
        val game = current.game ?: return
        collectionWrites.launch { updateCollection.setCaught(game, pokemonId, !current.caught) }
    }

    private fun toggleFavorite() {
        val favorite = state.value.favorite
        collectionWrites.launch { updateCollection.setFavorite(pokemonId, !favorite) }
    }

    /** Demande à la carte de surligner les lieux du Pokémon. */
    private fun showOnMap() {
        val details = state.value.details ?: return
        mapRequests.send(MapRequest.HighlightPokemon(details.id, details.name))
    }

    private fun catchState(game: Game, details: PokemonDetails, input: CatchInput): CatchUiState {
        // Niveau par défaut : le plus bas auquel on le rencontre dans la version.
        val level = input.level
            ?: details.encounters.filter { it.versionId == game.versionId && !it.isTrade }.minOfOrNull { it.minLevel }
            ?: DEFAULT_LEVEL
        val baseHp = details.stats.firstOrNull { it.identifier == HP }?.value ?: 0
        val maxHp = when (game.generation) {
            Generation.GEN1,
            Generation.GEN2 -> CatchRate.maxHp(baseHp, level)

            Generation.GEN3 -> Gen3CatchRate.maxHp(details.id, baseHp, level)
        }
        val currentHp = CatchRate.currentHp(maxHp, input.hp.fraction)
        val generation = checkNotNull(CaptureGeneration.from(game.generationId))
        val context = BallContext(
            details.id,
            details.weightHg,
            level,
            input.playerLevel,
            input.fishing,
            input.sameSpeciesAndGender,
            input.underwater,
            input.elapsedTurns,
            input.alreadyCaught,
            details.types.any { it.identifier == "water" || it.identifier == "bug" }
        )
        val blocked = if (generation == CaptureGeneration.GEN2 && Gen2CatchRate.blocksEngine(maxHp)) {
            generation.balls.filter { it != Ball.MASTER && it != Ball.LEVEL }.toSet()
        } else {
            emptySet()
        }
        val probabilities = generation.balls.filter { it !in blocked }.associateWith {
            generation.probability(it, details.captureRate, maxHp, currentHp, input.status, context)
        }
        return CatchUiState(
            level, input.hp, input.status, probabilities.toList(), CatchRate.bestBall(probabilities),
            generation, input.playerLevel, input.fishing, input.sameSpeciesAndGender,
            input.underwater, input.elapsedTurns, input.alreadyCaught, blocked
        )
    }

    companion object {
        const val POKEMON_ID = "pokemonId"
        private const val HP = "hp"
        private const val DEFAULT_LEVEL = 30
        const val MAX_LEVEL = 100
    }
}
