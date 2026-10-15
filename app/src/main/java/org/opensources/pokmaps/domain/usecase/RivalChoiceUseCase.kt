package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flatMapLatest
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.RivalSettings
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.model.Game

/** Pokémon de départ et combats indiqués par l'utilisateur, qui choisissent l'équipe montrée pour le rival. */
class RivalChoiceUseCase @Inject constructor(private val games: GameRepository, private val settings: RivalSettings) {
    /** Choix pour le jeu sélectionné. */
    @OptIn(ExperimentalCoroutinesApi::class)
    operator fun invoke(): Flow<RivalChoice> =
        games.selectedGame.flatMapLatest { settings.choice(it.versionGroupIdentifier) }

    suspend fun set(game: Game, choice: RivalChoice) = settings.set(game.versionGroupIdentifier, choice)
}
