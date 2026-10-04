package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry

@Singleton
class PokedexRepository @Inject constructor(private val dao: PokedexDao) {
    fun pokedex(game: Game): Flow<List<PokedexEntry>> = dao.pokedex(game.versionGroupId)
}
