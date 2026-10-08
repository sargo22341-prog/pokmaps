package org.opensources.pokmaps.ui.guide

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.guide.BreedingCatalog
import org.opensources.pokmaps.domain.guide.BreedingPair
import org.opensources.pokmaps.domain.guide.BreedingRules
import org.opensources.pokmaps.domain.guide.BreedingStatus
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.usecase.BreedingTools
import org.opensources.pokmaps.domain.usecase.BreedingUseCase

data class BreedingUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val catalog: BreedingCatalog? = null,
    val pair: BreedingPair? = null,
    val firstId: Int = 1,
    val secondId: Int = BreedingRules.DITTO,
    val first: ParentValues = ParentValues(ParentSex.FEMALE),
    val second: ParentValues = ParentValues(ParentSex.GENDERLESS)
) {
    val status: BreedingStatus? = pair?.let { BreedingRules.status(it, first, second) }
    val possible: Boolean = status == BreedingStatus.POSSIBLE || status == BreedingStatus.COMPATIBLE
    val firstMoves: List<LearnedMove> = pair?.first?.let {
        (it.levelUpMoves + it.machineMoves + it.eggMoves + it.tutorMoves).distinctBy { move ->
            move.moveId
        }.sortedBy { move -> move.name }
    }.orEmpty()
    val secondMoves: List<LearnedMove> = pair?.second?.let {
        (it.levelUpMoves + it.machineMoves + it.eggMoves + it.tutorMoves).distinctBy { move ->
            move.moveId
        }.sortedBy { move -> move.name }
    }.orEmpty()
    val firstSexes: List<ParentSex> = pair?.first?.let(BreedingRules::sexes).orEmpty()
    val secondSexes: List<ParentSex> = pair?.second?.let(BreedingRules::sexes).orEmpty()
    val offspringMoves: List<Pair<Int, List<LearnedMove>>> = if (possible) {
        pair?.babies.orEmpty().map { child ->
            val firstDonor = BreedingRules.donorIsFirst(requireNotNull(pair), first, second)
            child.id to BreedingRules.inherited(
                child,
                if (firstDonor) first.moves else second.moves,
                if (firstDonor) second.moves else first.moves
            )
        }
    } else {
        emptyList()
    }
}

sealed interface BreedingAction {
    data class Species(val first: Boolean, val id: Int) : BreedingAction
    data class Values(val first: Boolean, val values: ParentValues) : BreedingAction
    data object Retry : BreedingAction
}

@HiltViewModel
class BreedingViewModel internal constructor(private val tools: BreedingTools) : ViewModel() {
    @Inject constructor(tools: BreedingUseCase) : this(tools as BreedingTools)

    private val mutableState = MutableStateFlow(BreedingUiState())
    val state: StateFlow<BreedingUiState> = mutableState.asStateFlow()
    private var loadJob: Job? = null
    private var pairJob: Job? = null

    init {
        load()
    }

    fun onAction(action: BreedingAction) {
        when (action) {
            is BreedingAction.Species -> {
                if (state.value.catalog?.pokemon?.none { it.pokemonId == action.id } != false) return
                mutableState.update {
                    if (action.first) {
                        it.copy(firstId = action.id, first = ParentValues(it.first.sex), pair = null)
                    } else {
                        it.copy(secondId = action.id, second = ParentValues(it.second.sex), pair = null)
                    }
                }
                loadPair()
            }

            is BreedingAction.Values -> {
                val previous = if (action.first) state.value.first else state.value.second
                if (previous.sex != action.values.sex) {
                    mutableState.update {
                        if (action.first) {
                            it.copy(first = action.values, pair = null)
                        } else {
                            it.copy(second = action.values, pair = null)
                        }
                    }
                    loadPair()
                } else {
                    mutableState.update {
                        if (action.first) it.copy(first = action.values) else it.copy(second = action.values)
                    }
                }
            }

            BreedingAction.Retry -> load()
        }
    }

    private fun load() {
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            attempt {
                tools.observe().collect { catalog ->
                    pairJob?.cancel()
                    mutableState.value = BreedingUiState(loading = false, catalog = catalog)
                    if (catalog.pokemon.isNotEmpty()) loadPair()
                }
            }
        }
    }

    private fun loadPair() {
        pairJob?.cancel()
        val snapshot = state.value
        val game = snapshot.catalog?.game ?: return
        mutableState.update { it.copy(loading = true, failed = false, pair = null) }
        pairJob = viewModelScope.launch {
            attempt {
                var pair = tools.pair(game, snapshot.firstId, snapshot.secondId, snapshot.first.sex)
                val first = snapshot.first.copy(sex = validSex(pair.first, snapshot.first.sex))
                val second = snapshot.second.copy(sex = validSex(pair.second, snapshot.second.sex))
                if (first.sex !=
                    snapshot.first.sex
                ) {
                    pair = tools.pair(game, snapshot.firstId, snapshot.secondId, first.sex)
                }
                mutableState.update { it.copy(loading = false, pair = pair, first = first, second = second) }
            }
        }
    }

    private fun validSex(
        pokemon: org.opensources.pokmaps.domain.pokemon.PokemonDetails,
        selected: ParentSex
    ): ParentSex {
        val sexes = BreedingRules.sexes(pokemon)
        return if (selected in sexes) selected else sexes.first()
    }

    private suspend fun attempt(block: suspend () -> Unit) {
        try {
            block()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            mutableState.update { it.copy(loading = false, failed = true) }
        }
    }
}
