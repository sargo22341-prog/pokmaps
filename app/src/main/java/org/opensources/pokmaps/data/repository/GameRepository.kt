package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filterNotNull
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.Game

@Singleton
class GameRepository @Inject constructor(private val dao: GameDao, private val settings: GameSettings) {
    val games: Flow<List<Game>> = dao.games()

    /** Jeu choisi ; le premier jeu (Rouge) par défaut. */
    val selectedGame: Flow<Game> =
        combine(games, settings.selectedVersionId) { games, versionId ->
            games.firstOrNull { it.versionId == versionId } ?: games.firstOrNull()
        }.filterNotNull().distinctUntilChanged()

    suspend fun select(game: Game) = settings.selectVersion(game.versionId)
}
