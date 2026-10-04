package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.domain.model.Game

class ObserveGamesUseCase @Inject constructor(private val repository: GameRepository) {
    operator fun invoke(): Flow<List<Game>> = repository.games
}

class ObserveSelectedGameUseCase @Inject constructor(private val repository: GameRepository) {
    operator fun invoke(): Flow<Game> = repository.selectedGame
}

class SelectGameUseCase @Inject constructor(private val repository: GameRepository) {
    suspend operator fun invoke(game: Game) = repository.select(game)
}
