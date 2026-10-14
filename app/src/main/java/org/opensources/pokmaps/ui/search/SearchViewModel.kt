package org.opensources.pokmaps.ui.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.ItemSummary
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.opensources.pokmaps.domain.pokedex.PokedexSearch
import org.opensources.pokmaps.domain.pokedex.PokedexSearchIndex
import org.opensources.pokmaps.domain.usecase.ObserveSearchIndexUseCase
import org.opensources.pokmaps.domain.usecase.SearchIndex
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

/** Lieu trouvé : ville, route ou carte intérieure. */
data class PlaceResult(val identifier: String, val name: String, val outdoor: Boolean)

/** Personnage trouvé : dresseur, personnage ou installation proposant des offres ou des services. */
data class CharacterResult(val obj: MapObject, val name: String, val mapName: String, val offers: List<OfferLink>) {
    val roles: List<CharacterRole> get() = CharacterRole.of(obj.kind, offers.map { it.kind })
}

data class SearchUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val game: Game? = null,
    val query: String = "",
    val pokemon: List<PokedexEntry> = emptyList(),
    val places: List<PlaceResult> = emptyList(),
    val items: List<ItemSummary> = emptyList(),
    val characters: List<CharacterResult> = emptyList(),
    /** Ce que deviennent les fossiles du jeu, pour un personnage trouvé qui en donne. */
    val fossilUses: Map<String, FossilUse> = emptyMap()
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
 * Index et filtrage tournent sur `computation` : seul l'état final est publié sur le fil principal.
 */
@HiltViewModel
class SearchViewModel @Inject constructor(observeIndex: ObserveSearchIndexUseCase, computation: CoroutineDispatcher) :
    ViewModel() {
    private val query = MutableStateFlow("")

    /** Textes normalisés de chaque élément, calculés une fois par jeu. */
    private class Index(
        val source: SearchIndex,
        val pokemon: PokedexSearchIndex,
        val places: List<Pair<String, PlaceResult>>,
        val items: List<Pair<String, ItemSummary>>,
        val characters: List<Pair<String, CharacterResult>>,
        val fossilUses: Map<String, FossilUse>
    )

    /** Résultats calculés hors du fil principal ; ils peuvent correspondre au texte précédent un court instant. */
    private val results =
        combine(observeIndex().map(::index), query) { index, query -> results(index, query) }
            .flowOn(computation)
            .catch { emit(SearchUiState(loading = false, failed = true)) }
            .onStart { emit(SearchUiState()) }

    /**
     * Le texte saisi rejoint l'état sans attendre le calcul : un champ qui reçoit sa propre valeur en retard
     * replace son curseur et inverse l'ordre des lettres tapées.
     */
    val state: StateFlow<SearchUiState> =
        combine(results, query) { results, query -> results.copy(query = query) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SearchUiState())

    fun onAction(action: SearchAction) {
        when (action) {
            is SearchAction.Query -> query.value = action.text
        }
    }

    private fun results(index: Index, query: String): SearchUiState {
        val text = PokedexSearch.normalize(query)
        if (text.isEmpty()) return SearchUiState(loading = false, game = index.source.game, query = query)
        return SearchUiState(
            loading = false,
            game = index.source.game,
            query = query,
            pokemon = index.pokemon.filter(index.source.pokedex, PokedexFilter(query = query), MAX_RESULTS),
            places = index.places.matching(text),
            items = index.items.matching(text),
            characters = index.characters.matching(text),
            fossilUses = index.fossilUses
        )
    }

    private fun <T> List<Pair<String, T>>.matching(text: String): List<T> =
        asSequence().filter { (key, _) -> key.contains(text) }.take(MAX_RESULTS).map { it.second }.toList()

    private fun index(source: SearchIndex): Index {
        val catalog = source.catalog
        val places = catalog.searchableMaps()
            .sortedWith(compareBy({ it.parentId == null }, { it.id }))
            .map { map ->
                PokedexSearch.normalize(map.name) to PlaceResult(
                    map.identifier,
                    map.name,
                    catalog.displayedMapOf(map.id)?.isWorld == true
                )
            }
        val items = source.index.items.sortedBy { it.name }.map { item ->
            PokedexSearch.normalize(listOfNotNull(item.name, item.moveName).joinToString(" ")) to item
        }
        val offers = source.index.offers.groupBy { it.objectId }
        val characters = catalog.objectsById.values
            .filter { it.kind == MapObjectKind.TRAINER || (it.kind in OFFERING_KINDS && it.id in offers) }
            .sortedBy { it.id }
            .map { obj ->
                val links = offers[obj.id].orEmpty()
                val result = CharacterResult(obj, obj.name, catalog.maps[obj.mapId]?.name.orEmpty(), links)
                val names = links.flatMap {
                    listOfNotNull(it.itemName, it.pokemonName, it.wantedPokemonName, it.wantedItemName)
                }
                PokedexSearch.normalize((listOf(result.name) + names).joinToString(" ")) to result
            }
        return Index(
            source,
            PokedexSearchIndex(source.pokedex),
            places,
            items,
            characters,
            FossilUse.of(source.index, catalog)
        )
    }

    private companion object {
        const val MAX_RESULTS = 50

        /** Personnages et installations listés quand ils proposent quelque chose. */
        val OFFERING_KINDS = setOf(
            MapObjectKind.NPC,
            MapObjectKind.NPC_OBJECT,
            MapObjectKind.NPC_POKEMON,
            MapObjectKind.VENDING_MACHINE,
            MapObjectKind.PRIZE_VENDOR,
            MapObjectKind.HEAL_SPOT
        )
    }
}
