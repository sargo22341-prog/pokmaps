package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flatMapLatest
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.model.PokedexEntry

/** Pokédex du jeu choisi, mis à jour quand l'utilisateur change de jeu. */
class ObservePokedexUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository
) {
    @OptIn(ExperimentalCoroutinesApi::class)
    operator fun invoke(): Flow<List<PokedexEntry>> = games.selectedGame.flatMapLatest { pokedex.pokedex(it) }
}
