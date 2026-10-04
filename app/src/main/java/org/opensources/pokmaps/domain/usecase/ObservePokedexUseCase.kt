package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType

/** Pokédex du jeu choisi et types de sa génération (pour les filtres). */
data class Pokedex(val game: Game, val entries: List<PokedexEntry>, val types: List<PokemonType>)

/** Pokédex du jeu choisi, mis à jour quand l'utilisateur change de jeu. */
class ObservePokedexUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository
) {
    operator fun invoke(): Flow<Pokedex> = games.selectedGame.map {
        Pokedex(it, pokedex.pokedex(it), pokedex.types(it))
    }
}
