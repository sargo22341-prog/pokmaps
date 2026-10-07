package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MoveRepository
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.MoveDetails

/** Fiche d'une attaque dans le jeu choisi (null si le jeu ne la connaît pas). */
data class MovePage(val game: Game, val details: MoveDetails?)

class ObserveMoveUseCase @Inject constructor(private val games: GameRepository, private val moves: MoveRepository) {
    operator fun invoke(moveId: Int): Flow<MovePage> =
        games.selectedGame.map { MovePage(it, moves.details(it, moveId)) }
}
