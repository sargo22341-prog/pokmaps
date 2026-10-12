package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.map.GameIndex
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry

/** Tout ce que parcourt la recherche globale dans le jeu choisi. */
data class SearchIndex(val game: Game, val pokedex: List<PokedexEntry>, val catalog: MapCatalog, val index: GameIndex)

class ObserveSearchIndexUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository,
    private val maps: MapRepository
) {
    operator fun invoke(): Flow<SearchIndex> = games.selectedGame.map {
        SearchIndex(it, pokedex.pokedex(it), maps.catalog(it), maps.index(it))
    }
}
