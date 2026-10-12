package org.opensources.pokmaps.data.repository

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakePokedexDao
import org.opensources.pokmaps.data.db.PokedexDao

class PokedexRepositoryTest {
    private class CountingDao : PokedexDao by FakePokedexDao() {
        private val source = FakePokedexDao()
        var catalogReads = 0
        var typeReads = 0
        var pokemonTypeReads = 0
        var methodReads = 0

        override suspend fun catalogs(versionGroupId: Int) = source.catalogs(versionGroupId).also { catalogReads++ }

        override suspend fun pokemonTypes(generationId: Int) = source.pokemonTypes(generationId)
            .also { pokemonTypeReads++ }

        override suspend fun encounterMethods(versionId: Int) = source.encounterMethods(versionId)
            .also { methodReads++ }

        override suspend fun types(generationId: Int) = source.types(generationId).also { typeReads++ }
    }

    @Test
    fun referencesAreSharedOnlyWithinTheirContextAndReloadAfterReplacement() = runTest {
        val dao = CountingDao()
        val repository = PokedexRepository(dao)
        for (game in listOf(FakeGameDao.RED, FakeGameDao.BLUE)) {
            repository.catalogs(game)
            repository.pokedex(game)
            repository.pokedex(game)
            repository.types(game)
        }
        assertEquals(1, dao.catalogReads)
        assertEquals(1, dao.typeReads)
        assertEquals(1, dao.pokemonTypeReads)
        assertEquals(2, dao.methodReads)
        repository.catalogs(FakeGameDao.GOLD)
        repository.types(FakeGameDao.GOLD)
        repository.catalogs(FakeGameDao.RED)
        repository.types(FakeGameDao.RED)
        assertEquals(3, dao.catalogReads)
        assertEquals(3, dao.typeReads)
        assertEquals(
            setOf(23, 133),
            repository.pokedex(FakeGameDao.RED)
                .filter {
                    org.opensources.pokmaps.domain.model.ObtainMethod.WALK in it.obtainMethods ||
                        org.opensources.pokmaps.domain.model.ObtainMethod.GIFT in it.obtainMethods
                }.map { it.pokemonId }.toSet()
        )
        assertEquals(
            setOf(27, 133),
            repository.pokedex(FakeGameDao.BLUE)
                .filter {
                    org.opensources.pokmaps.domain.model.ObtainMethod.WALK in it.obtainMethods ||
                        org.opensources.pokmaps.domain.model.ObtainMethod.GIFT in it.obtainMethods
                }.map { it.pokemonId }.toSet()
        )
    }
}
