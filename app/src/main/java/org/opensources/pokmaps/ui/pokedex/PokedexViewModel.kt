package org.opensources.pokmaps.ui.pokedex

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.opensources.pokmaps.domain.pokedex.PokedexSearch
import org.opensources.pokmaps.domain.usecase.ObservePokedexUseCase
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class PokedexUiState(
    val loading: Boolean = true,
    val game: Game? = null,
    /** Pokémon correspondant à la recherche et aux filtres. */
    val entries: List<PokedexEntry> = emptyList(),
    val total: Int = 0,
    val types: List<PokemonType> = emptyList(),
    val filter: PokedexFilter = PokedexFilter()
)

@HiltViewModel
class PokedexViewModel @Inject constructor(observePokedex: ObservePokedexUseCase) : ViewModel() {
    private val filter = MutableStateFlow(PokedexFilter())

    val state: StateFlow<PokedexUiState> =
        combine(observePokedex(), filter) { pokedex, filter ->
            // Un type absent de la génération du nouveau jeu n'a plus de sens comme filtre.
            val activeFilter = if (pokedex.types.any { it.id == filter.typeId }) filter else filter.copy(typeId = null)
            PokedexUiState(
                loading = false,
                game = pokedex.game,
                entries = PokedexSearch.filter(pokedex.entries, activeFilter),
                total = pokedex.entries.size,
                types = pokedex.types,
                filter = activeFilter
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PokedexUiState())

    fun search(query: String) = filter.update { it.copy(query = query) }

    fun filterType(typeId: Int?) = filter.update { it.copy(typeId = typeId) }

    fun filterMethod(method: ObtainMethod?) = filter.update { it.copy(method = method) }

    fun toggleAvailableOnly() = filter.update { it.copy(availableOnly = !it.availableOnly) }

    fun resetFilters() = filter.update { PokedexFilter(query = it.query) }
}
