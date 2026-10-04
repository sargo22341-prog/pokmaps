package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

/** Fiche d'un Pokémon dans le jeu choisi (null si le Pokémon n'existe pas). */
data class PokemonPage(val game: Game, val details: PokemonDetails?)

class ObservePokemonUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokemon: PokemonRepository
) {
    operator fun invoke(pokemonId: Int): Flow<PokemonPage> =
        games.selectedGame.map { PokemonPage(it, pokemon.details(it, pokemonId)) }
}
