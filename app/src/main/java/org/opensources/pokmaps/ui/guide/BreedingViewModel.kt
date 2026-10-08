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
import org.opensources.pokmaps.domain.guide.BreedingPartners
import org.opensources.pokmaps.domain.guide.BreedingRules
import org.opensources.pokmaps.domain.guide.BreedingStatus
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.opensources.pokmaps.domain.pokedex.PokedexSearch
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.usecase.BreedingTools
import org.opensources.pokmaps.domain.usecase.BreedingUseCase

data class BreedingUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val catalog: BreedingCatalog? = null,
    val pair: BreedingPair? = null,
    val firstId: Int = 1,
    val secondId: Int = 1,
    val firstSelected: Boolean = false,
    val first: ParentValues = ParentValues(ParentSex.FEMALE),
    val second: ParentValues = ParentValues(ParentSex.GENDERLESS),
    val query: String = ""
) {
    val partners: List<PokedexEntry> = catalog?.let { catalog ->
        val profile = catalog.profiles[firstId] ?: return@let emptyList()
        catalog.pokemon.filter { entry ->
            catalog.profiles[entry.pokemonId]?.let { BreedingPartners.compatible(profile, first.sex, it) } == true
        }
    }.orEmpty()
    val partnerChoices: List<PokedexEntry> = PokedexSearch.filter(partners, PokedexFilter(query = query))
    val choices: List<PokedexEntry> = PokedexSearch.filter(catalog?.pokemon.orEmpty(), PokedexFilter(query = query))
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
    val secondSexes: List<ParentSex> = pair?.second?.let(BreedingRules::sexes).orEmpty().filter {
        firstId == BreedingRules.DITTO || secondId == BreedingRules.DITTO || it == BreedingPartners.opposite(first.sex)
    }
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
    data class Search(val query: String) : BreedingAction
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
            is BreedingAction.Species -> selectSpecies(action)
            is BreedingAction.Values -> changeValues(action)
            is BreedingAction.Search -> mutableState.update { it.copy(query = action.query.take(100)) }
            BreedingAction.Retry -> load()
        }
    }

    private fun selectSpecies(action: BreedingAction.Species) {
        val allowed = if (action.first) state.value.catalog?.pokemon.orEmpty() else state.value.partners
        if (allowed.none { it.pokemonId == action.id }) return
        mutableState.update {
            if (action.first) {
                val sex = it.catalog?.profiles?.get(action.id)?.sexes?.let { sexes ->
                    if (ParentSex.FEMALE in sexes) ParentSex.FEMALE else sexes.first()
                } ?: ParentSex.FEMALE
                it.copy(firstId = action.id, firstSelected = true, first = ParentValues(sex), pair = null)
            } else {
                it.copy(secondId = action.id, second = ParentValues(it.second.sex), pair = null)
            }
        }
        if (action.first) resetPartner()
        loadPair()
    }

    private fun changeValues(action: BreedingAction.Values) {
        val sexes = if (action.first) state.value.firstSexes else state.value.secondSexes
        if (action.values.sex !in sexes) return
        val previous = if (action.first) state.value.first else state.value.second
        if (previous.sex != action.values.sex) {
            mutableState.update {
                if (action.first) {
                    it.copy(first = action.values, pair = null)
                } else {
                    it.copy(second = action.values, pair = null)
                }
            }
            if (action.first) resetPartner()
            loadPair()
        } else {
            mutableState.update {
                if (action.first) it.copy(first = action.values) else it.copy(second = action.values)
            }
        }
    }

    private fun load() {
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            attempt {
                tools.observe().collect { catalog ->
                    pairJob?.cancel()
                    val current = state.value
                    val retained = current.firstSelected && current.catalog?.game == catalog.game
                    mutableState.value = if (retained) {
                        current.copy(catalog = catalog, loading = false, failed = false)
                    } else {
                        BreedingUiState(loading = false, catalog = catalog)
                    }
                    if (retained) loadPair()
                }
            }
        }
    }

    private fun resetPartner() {
        mutableState.update { current ->
            val id = BreedingPartners.defaultPartner(current.firstId, current.partners.map { it.pokemonId })
                ?: current.firstId
            val sexes = current.catalog?.profiles?.get(id)?.sexes.orEmpty()
            val opposite = BreedingPartners.opposite(current.first.sex)
            val sex = if (opposite in sexes) opposite else sexes.firstOrNull() ?: ParentSex.GENDERLESS
            current.copy(secondId = id, second = ParentValues(sex))
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
                val preferred = if (snapshot.firstId == BreedingRules.DITTO ||
                    snapshot.secondId == BreedingRules.DITTO
                ) {
                    snapshot.second.sex
                } else {
                    BreedingPartners.opposite(first.sex)
                }
                val second = snapshot.second.copy(sex = validSex(pair.second, preferred))
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
