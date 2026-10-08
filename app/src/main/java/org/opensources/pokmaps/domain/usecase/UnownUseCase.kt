package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.UnownSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.UnownForm

data class UnownCollection(val game: Game, val forms: List<UnownForm>, val caught: Set<UnownForm>)

class UnownUseCase @Inject constructor(
    private val games: GameRepository,
    private val settings: UnownSettings,
    private val collection: CollectionSettings
) {
    fun observe() = combine(games.selectedGame, games.games, settings.caught, collection.captureScope) {
            game,
            allGames,
            caught,
            scope
        ->
        val forms = UnownForm.available(game.generationId)
        val recorded = scope.versionsFor(game, allGames, caught.keys).flatMap { caught[it].orEmpty() }.toSet()
        UnownCollection(game, forms, recorded.intersect(forms.toSet()))
    }

    suspend fun setCaught(game: Game, form: UnownForm, caught: Boolean) {
        require(form in UnownForm.available(game.generationId))
        val versions = if (caught) {
            setOf(game.versionId)
        } else {
            collection.captureScope.first().versionsFor(game, games.games.first(), settings.caught.first().keys)
        }
        settings.setCaught(versions, form, caught)
    }
}
