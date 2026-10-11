package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flowOf
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.PokedexCatalog

/** Pokédex du jeu choisi et types de sa génération (pour les filtres). */
data class Pokedex(
    val game: Game,
    val entries: List<PokedexEntry>,
    val types: List<PokemonType>,
    val catalogs: List<PokedexCatalog>,
    val selectedId: Int
)

/** Pokédex du jeu choisi, mis à jour quand l'utilisateur change de jeu. */
class ObservePokedexUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository
) {
    operator fun invoke(selection: Flow<Pair<Int, Int>?> = flowOf(null)): Flow<Pokedex> =
        combine(games.selectedGame, selection) { game, selection ->
            val catalogs = pokedex.catalogs(game)
            check(catalogs.isNotEmpty()) { "Aucun Pokédex pour ${game.versionIdentifier}" }
            val selected = catalogs.firstOrNull { selection == (game.versionId to it.id) } ?: catalogs.first()
            Pokedex(game, pokedex.pokedex(game, selected.id), pokedex.types(game), catalogs, selected.id)
        }
}
