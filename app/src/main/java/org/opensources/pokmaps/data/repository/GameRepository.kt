package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup

@Singleton
class GameRepository @Inject constructor(private val dao: GameDao, private val settings: GameSettings) {
    val games: Flow<List<Game>> = dao.games().map { games ->
        check(games.isNotEmpty()) { "Catalogue de jeux vide" }
        val unsupported = games.filterNot { VersionGroup.isSupported(it.versionGroupIdentifier) }
        check(unsupported.isEmpty()) {
            "Jeux sans règles dans l'application : ${unsupported.joinToString { it.versionIdentifier }}"
        }
        games.forEach { game ->
            check(game.version.identifier == game.versionIdentifier && game.version.group == game.versionGroup) {
                "Version incohérente : ${game.versionIdentifier}"
            }
            check(game.version.generation == game.generation) { "Génération incohérente : ${game.versionIdentifier}" }
        }
        games
    }

    /** Jeu choisi ; le premier jeu (Rouge) par défaut. */
    val selectedGame: Flow<Game> =
        combine(games, settings.selectedVersionId) { games, versionId ->
            games.firstOrNull { it.versionId == versionId } ?: games.first()
        }.distinctUntilChanged()

    suspend fun select(game: Game) = settings.selectVersion(game.versionId)
}
