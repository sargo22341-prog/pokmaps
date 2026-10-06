package org.opensources.pokmaps.ui.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.map.ItemSummary
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.opensources.pokmaps.domain.pokedex.PokedexSearch
import org.opensources.pokmaps.domain.usecase.ObserveSearchIndexUseCase
import org.opensources.pokmaps.domain.usecase.SearchIndex
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

/** Lieu trouvé : ville, route ou carte intérieure. */
data class PlaceResult(val identifier: String, val name: String, val outdoor: Boolean)

/** Personnage trouvé : dresseur, ou personnage qui donne, vend ou échange quelque chose. */
data class CharacterResult(val obj: MapObject, val name: String, val mapName: String, val offers: List<OfferLink>)

data class SearchUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val game: Game? = null,
    val query: String = "",
    val pokemon: List<PokedexEntry> = emptyList(),
    val places: List<PlaceResult> = emptyList(),
    val items: List<ItemSummary> = emptyList(),
    val characters: List<CharacterResult> = emptyList()
) {
    val isEmpty: Boolean get() = pokemon.isEmpty() && places.isEmpty() && items.isEmpty() && characters.isEmpty()
}

/** Intentions de l'écran de recherche. */
sealed interface SearchAction {
    data class Query(val text: String) : SearchAction
}

/**
 * Recherche globale dans le jeu choisi : Pokémon, lieux, objets (et l'attaque des CT / CS) et personnages
 * (par leur nom ou ce qu'ils donnent, vendent ou échangent). Accents et casse ignorés.
 */
@HiltViewModel
class SearchViewModel @Inject constructor(observeIndex: ObserveSearchIndexUseCase) : ViewModel() {
    private val query = MutableStateFlow("")

    /** Textes normalisés de chaque élément, calculés une fois par jeu. */
    private class Index(
        val source: SearchIndex,
        val places: List<Pair<String, PlaceResult>>,
        val items: List<Pair<String, ItemSummary>>,
        val characters: List<Pair<String, CharacterResult>>
    )

    val state: StateFlow<SearchUiState> =
        combine(observeIndex().map(::index), query) { index, query ->
            val text = PokedexSearch.normalize(query)
            if (text.isEmpty()) {
                SearchUiState(loading = false, game = index.source.game, query = query)
            } else {
                SearchUiState(
                    loading = false,
                    game = index.source.game,
                    query = query,
                    pokemon = PokedexSearch.filter(index.source.pokedex, PokedexFilter(query = query))
                        .take(MAX_RESULTS),
                    places = index.places.matching(text),
                    items = index.items.matching(text),
                    characters = index.characters.matching(text)
                )
            }
        }.catch { emit(SearchUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SearchUiState())

    fun onAction(action: SearchAction) {
        when (action) {
            is SearchAction.Query -> query.value = action.text
        }
    }

    private fun <T> List<Pair<String, T>>.matching(text: String): List<T> =
        filter { (key, _) -> key.contains(text) }.take(MAX_RESULTS).map { it.second }

    private fun index(source: SearchIndex): Index {
        val catalog = source.catalog
        val places = catalog.maps.values
            .filter { it.identifier != GameMap.WORLD }
            .sortedWith(compareBy({ it.parentId == null }, { it.id }))
            .map { map ->
                PokedexSearch.normalize(map.name) to PlaceResult(map.identifier, map.name, map.parentId != null)
            }
        val items = source.index.items.sortedBy { it.name }.map { item ->
            PokedexSearch.normalize(listOfNotNull(item.name, item.moveName).joinToString(" ")) to item
        }
        val offers = source.index.offers.groupBy { it.objectId }
        val characters = catalog.objectsById.values
            .filter { it.kind == MapObjectKind.TRAINER || (it.kind == MapObjectKind.NPC && it.id in offers) }
            .sortedBy { it.id }
            .map { obj ->
                val links = offers[obj.id].orEmpty()
                val result = CharacterResult(obj, obj.name, catalog.maps[obj.mapId]?.name.orEmpty(), links)
                val names = links.flatMap { listOfNotNull(it.itemName, it.pokemonName, it.wantedPokemonName) }
                PokedexSearch.normalize((listOf(result.name) + names).joinToString(" ")) to result
            }
        return Index(source, places, items, characters)
    }

    private companion object {
        const val MAX_RESULTS = 50
    }
}
