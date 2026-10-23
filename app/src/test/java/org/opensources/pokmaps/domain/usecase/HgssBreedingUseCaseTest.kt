package org.opensources.pokmaps.domain.usecase

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakePokedexDao
import org.opensources.pokmaps.data.db.FakePokemonDao
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.guide.BreedingItem
import org.opensources.pokmaps.domain.guide.HgssBreeding
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues

class HgssBreedingUseCaseTest {
    @Test
    fun bothCartridgesReadGroupTenAndKeepTheirOwnIdentityThroughPairResolution() = runTest {
        for (game in listOf(FakeGameDao.HEARTGOLD, FakeGameDao.SOULSILVER)) {
            val reads = mutableListOf<Int>()
            val delegate = FakePokemonDao()
            val dao = object : PokemonDao by delegate {
                override suspend fun profile(pokemonId: Int, versionGroupId: Int) =
                    delegate.profile(pokemonId, versionGroupId).also { reads += versionGroupId }
            }
            val pokedex = PokedexRepository(FakePokedexDao(national = true))
            val tools = BreedingUseCase(
                GameRepository(FakeGameDao(listOf(game)), GameSettings(FakeDataStore())),
                pokedex,
                PokemonRepository(dao, pokedex)
            )
            assertEquals(game, tools.observe().first().game)
            val pair = tools.pair(game, 25, 25, ParentSex.FEMALE)
            assertEquals(4, pair.generationId)
            assertEquals(listOf(25), pair.babies.map { it.id })
            assertEquals(listOf(10, 10, 10), reads)
            val mother = ParentValues(ParentSex.FEMALE)
            val father = ParentValues(ParentSex.MALE, item = BreedingItem.EVERSTONE)
            assertEquals(listOf(1), HgssBreeding.natureParents(mother, father))
        }
    }
}
