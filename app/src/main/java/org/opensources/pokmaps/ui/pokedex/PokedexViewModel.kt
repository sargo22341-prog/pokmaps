package org.opensources.pokmaps.ui.pokedex

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
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.CaughtFilter
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.opensources.pokmaps.domain.pokedex.PokedexSearch
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokedexUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class PokedexUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val game: Game? = null,
    /** Pokémon correspondant à la recherche et aux filtres. */
    val entries: List<PokedexEntry> = emptyList(),
    val total: Int = 0,
    /** Pokémon capturés dans la version choisie. */
    val caughtCount: Int = 0,
    val types: List<PokemonType> = emptyList(),
    val filter: PokedexFilter = PokedexFilter()
)

/** Intentions de l'écran du Pokédex. */
sealed interface PokedexAction {
    data class Search(val query: String) : PokedexAction

    data class FilterType(val typeId: Int?) : PokedexAction

    data class FilterMethod(val method: ObtainMethod?) : PokedexAction

    data class FilterCaught(val caught: CaughtFilter) : PokedexAction

    data object ToggleAvailableOnly : PokedexAction

    data object ToggleFavoritesOnly : PokedexAction

    /** Efface les filtres, en gardant la recherche. */
    data object ResetFilters : PokedexAction

    /** Coche ou décoche « capturé » dans la version choisie. */
    data class ToggleCaught(val entry: PokedexEntry) : PokedexAction

    data class ToggleFavorite(val entry: PokedexEntry) : PokedexAction
}

@HiltViewModel
class PokedexViewModel @Inject constructor(
    observePokedex: ObservePokedexUseCase,
    observeCollection: ObserveCollectionUseCase,
    private val updateCollection: UpdateCollectionUseCase
) : ViewModel() {
    private val filter = MutableStateFlow(PokedexFilter())

    val state: StateFlow<PokedexUiState> =
        combine(observePokedex(), observeCollection(), filter) { pokedex, collection, filter ->
            // Un type absent de la génération du nouveau jeu n'a plus de sens comme filtre.
            val activeFilter = if (pokedex.types.any { it.id == filter.typeId }) filter else filter.copy(typeId = null)
            // Captures de la version affichée (la collection peut avoir un temps de retard au changement de jeu).
            val caught = if (collection.game == pokedex.game) collection.caught else emptySet()
            val entries = pokedex.entries.map {
                it.copy(caught = it.pokemonId in caught, favorite = it.pokemonId in collection.favorites)
            }
            PokedexUiState(
                loading = false,
                game = pokedex.game,
                entries = PokedexSearch.filter(entries, activeFilter),
                total = pokedex.entries.size,
                caughtCount = entries.count { it.caught },
                types = pokedex.types,
                filter = activeFilter
            )
        }.catch { emit(PokedexUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PokedexUiState())

    fun onAction(action: PokedexAction) {
        when (action) {
            is PokedexAction.Search -> filter.update { it.copy(query = action.query) }
            is PokedexAction.FilterType -> filter.update { it.copy(typeId = action.typeId) }
            is PokedexAction.FilterMethod -> filter.update { it.copy(method = action.method) }
            is PokedexAction.FilterCaught -> filter.update { it.copy(caught = action.caught) }
            PokedexAction.ToggleAvailableOnly -> filter.update { it.copy(availableOnly = !it.availableOnly) }
            PokedexAction.ToggleFavoritesOnly -> filter.update { it.copy(favoritesOnly = !it.favoritesOnly) }
            PokedexAction.ResetFilters -> filter.update { PokedexFilter(query = it.query) }
            is PokedexAction.ToggleCaught -> toggleCaught(action.entry)
            is PokedexAction.ToggleFavorite -> toggleFavorite(action.entry)
        }
    }

    private fun toggleCaught(entry: PokedexEntry) {
        val game = state.value.game ?: return
        viewModelScope.launch { updateCollection.setCaught(game, entry.pokemonId, !entry.caught) }
    }

    private fun toggleFavorite(entry: PokedexEntry) {
        viewModelScope.launch { updateCollection.setFavorite(entry.pokemonId, !entry.favorite) }
    }
}
