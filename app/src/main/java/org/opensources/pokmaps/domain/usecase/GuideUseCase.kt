package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import org.opensources.pokmaps.data.guide.GuideRepository
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.retro.RetroRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.GuideSettings
import org.opensources.pokmaps.data.settings.UnownSettings
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideProgress

/** Contrat substitué en mémoire dans les tests des états et des écritures du guide. */
interface Guides {
    fun observe(): Flow<Pair<GuideLibrary, GuideProgress>>
    suspend fun complete(versionId: Int, id: String, completed: Boolean)
}

class GuideUseCase @Inject constructor(
    private val games: GameRepository,
    private val repository: GuideRepository,
    private val settings: GuideSettings,
    private val collection: CollectionSettings,
    private val retro: RetroRepository,
    private val unown: UnownSettings
) : Guides {
    @OptIn(ExperimentalCoroutinesApi::class)
    override fun observe(): Flow<Pair<GuideLibrary, GuideProgress>> = games.selectedGame.flatMapLatest { game ->
        flow {
            val library = repository.library(game)
            emit(library)
        }.combine(settings.progress(game.versionId)) { library, progress -> library to progress }
            .combine(collection.caughtByVersion) { (library, progress), caught ->
                library.copy(caught = caught[library.game.versionId].orEmpty()) to progress
            }
            .combine(retro.observe()) { (library, progress), remote -> library.copy(retro = remote) to progress }
            .combine(unown.caught) { (library, progress), forms ->
                library.copy(unown = forms[library.game.versionId].orEmpty()) to progress
            }
    }.flowOn(Dispatchers.IO)

    override suspend fun complete(versionId: Int, id: String, completed: Boolean) =
        settings.complete(versionId, id, completed)
}
