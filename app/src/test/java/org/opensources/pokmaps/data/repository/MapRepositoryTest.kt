package org.opensources.pokmaps.data.repository

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.domain.map.MapCatalog

class MapRepositoryTest {
    @Test
    fun catalogKeepsTheObjectsOfEachVersion() = runTest {
        val repository = MapRepository(FakeMapDao(includeVersionPokemon = true))

        fun level(catalog: MapCatalog): Int? =
            catalog.objects.getValue(FakeMapDao.ROUTE_1).single { it.pokemonId == FakeMapDao.SNORLAX }.level

        // Rouge et Bleu partagent leurs cartes, mais pas ce Pokémon fixe : chaque version a son catalogue.
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.RED)))
        assertEquals(FakeMapDao.BLUE_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.BLUE)))
    }
}
