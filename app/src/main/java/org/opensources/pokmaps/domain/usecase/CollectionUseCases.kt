package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.domain.model.Game

/** Pokémon capturés dans la version du jeu choisi, et favoris (communs à tous les jeux). */
data class PokemonCollection(val game: Game, val caught: Set<Int>, val favorites: Set<Int>)

class ObserveCollectionUseCase @Inject constructor(
    private val games: GameRepository,
    private val settings: CollectionSettings
) {
    @OptIn(ExperimentalCoroutinesApi::class)
    operator fun invoke(): Flow<PokemonCollection> = games.selectedGame.flatMapLatest { game ->
        combine(settings.caught(game.versionId), settings.favorites) { caught, favorites ->
            PokemonCollection(game, caught, favorites)
        }
    }
}

class UpdateCollectionUseCase @Inject constructor(private val settings: CollectionSettings) {
    suspend fun setCaught(game: Game, pokemonId: Int, caught: Boolean) =
        settings.setCaught(game.versionId, pokemonId, caught)

    suspend fun setFavorite(pokemonId: Int, favorite: Boolean) = settings.setFavorite(pokemonId, favorite)
}
