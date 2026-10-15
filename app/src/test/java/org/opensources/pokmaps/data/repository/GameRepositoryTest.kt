package org.opensources.pokmaps.data.repository

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings

class GameRepositoryTest {
    @Test(expected = IllegalStateException::class)
    fun aVersionIdentifierCannotDescribeAnotherCartridge(): Unit = runBlocking {
        val games = FakeGameDao(listOf(FakeGameDao.GOLD.copy(versionIdentifier = "crystal")))
        GameRepository(games, GameSettings(FakeDataStore())).games.first()
    }

    @Test(expected = IllegalStateException::class)
    fun aGenerationCannotDescribeAnotherCartridge(): Unit = runBlocking {
        val games = FakeGameDao(listOf(FakeGameDao.GOLD.copy(generationId = 1)))
        GameRepository(games, GameSettings(FakeDataStore())).games.first()
    }
}
