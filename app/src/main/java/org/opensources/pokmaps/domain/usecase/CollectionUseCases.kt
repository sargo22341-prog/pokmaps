package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokedex.CaptureScope

/**
 * Pokémon capturés pour le jeu choisi, selon la portée des captures (ce jeu, sa génération ou tous les jeux), et
 * favoris (communs à tous les jeux).
 */
data class PokemonCollection(
    val game: Game,
    val caught: Set<Int>,
    val favorites: Set<Int>,
    val scope: CaptureScope = CaptureScope.DEFAULT
)

class ObserveCollectionUseCase @Inject constructor(
    private val games: GameRepository,
    private val settings: CollectionSettings
) {
    operator fun invoke(): Flow<PokemonCollection> = combine(
        games.selectedGame,
        games.games,
        settings.caughtByVersion,
        settings.favorites,
        settings.captureScope
    ) { game, all, caughtByVersion, favorites, scope ->
        PokemonCollection(game, scope.caught(game, all, caughtByVersion), favorites, scope)
    }
}

class UpdateCollectionUseCase @Inject constructor(
    private val games: GameRepository,
    private val settings: CollectionSettings
) {
    /**
     * Une capture se mémorise dans la version du jeu choisi. La décocher la retire de toutes les versions qui
     * comptent pour la portée : sinon le Pokémon resterait capturé à cause d'un autre jeu.
     */
    suspend fun setCaught(game: Game, pokemonId: Int, caught: Boolean) {
        val versions = if (caught) {
            setOf(game.versionId)
        } else {
            val recorded = settings.caughtByVersion.first().keys
            settings.captureScope.first().versionsFor(game, games.games.first(), recorded)
        }
        settings.setCaught(versions, pokemonId, caught)
    }

    suspend fun setFavorite(pokemonId: Int, favorite: Boolean) = settings.setFavorite(pokemonId, favorite)
}

/** Réglage de la portée des captures. */
class CaptureScopeUseCase @Inject constructor(private val settings: CollectionSettings) {
    val scope: Flow<CaptureScope> = settings.captureScope

    suspend fun set(scope: CaptureScope) = settings.setCaptureScope(scope)
}
