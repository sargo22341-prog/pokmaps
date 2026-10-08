package org.opensources.pokmaps.domain.usecase

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.guide.BreedingPartners
import org.opensources.pokmaps.domain.guide.ParentSex
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class BreedingUseCaseTest {
    @Test
    fun realCatalogAndOffspringRespectSecondGenerationExceptions() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "breeding-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        try {
            val pokedex = PokedexRepository(database.pokedexDao())
            val pokemon = PokemonRepository(database.pokemonDao(), pokedex)
            val tools = BreedingUseCase(
                GameRepository(FakeGameDao(listOf(FakeGameDao.GOLD)), GameSettings(FakeDataStore())),
                pokedex,
                pokemon
            )
            val catalog = tools.observe().first()
            assertEquals(catalog.pokemon.map { it.pokemonId }.toSet(), catalog.profiles.keys)
            val profiles = catalog.profiles
            for (id in listOf(30, 31, 172, 173, 174, 175, 236, 238, 239, 240, 150, 151, 249, 250, 251)) {
                assertFalse("Espèce stérile $id", profiles.getValue(id).fertile)
            }
            assertTrue(BreedingPartners.compatible(profiles.getValue(81), ParentSex.GENDERLESS, profiles.getValue(132)))
            assertFalse(
                BreedingPartners.compatible(profiles.getValue(132), ParentSex.GENDERLESS, profiles.getValue(132))
            )
            assertEquals(listOf(29, 32), tools.pair(catalog.game, 29, 132, ParentSex.FEMALE).babies.map { it.id })
            assertEquals(listOf(32), tools.pair(catalog.game, 34, 132, ParentSex.MALE).babies.map { it.id })
            assertEquals(listOf(172), tools.pair(catalog.game, 25, 132, ParentSex.FEMALE).babies.map { it.id })
            assertEquals(listOf(81), tools.pair(catalog.game, 81, 132, ParentSex.GENDERLESS).babies.map { it.id })
        } finally {
            database.close()
        }
    }
}
