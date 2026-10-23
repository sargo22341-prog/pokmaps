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
import org.opensources.pokmaps.domain.guide.ParentSex
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class SinnohBreedingUseCaseTest {
    @Test
    fun allThreeGamesResolveIncenseBabiesManaphyAndSterileSpeciesFromTheDistributedDatabase() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "sinnoh-breeding-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database")))).build()
        try {
            val pokedex = PokedexRepository(database.pokedexDao())
            val pokemon = PokemonRepository(database.pokemonDao(), pokedex)
            val games = database.gameDao().games().first().filter { it.versionId in 12..14 }
            assertEquals(3, games.size)
            for (game in games) {
                val tools =
                    BreedingUseCase(
                        GameRepository(FakeGameDao(listOf(game)), GameSettings(FakeDataStore())),
                        pokedex,
                        pokemon
                    )
                val catalog = tools.observe().first()
                assertEquals(493, catalog.pokemon.size)
                assertFalse(catalog.profiles.getValue(30).fertile)
                assertFalse(catalog.profiles.getValue(31).fertile)
                assertTrue(catalog.profiles.getValue(490).fertile)
                val families = listOf(
                    298 to 183, 360 to 202, 406 to 315, 433 to 358, 438 to 185,
                    439 to 122, 440 to 113, 446 to 143, 458 to 226
                )
                for ((baby, adult) in families) {
                    assertEquals(
                        listOf(baby, adult),
                        tools.pair(game, adult, 132, ParentSex.FEMALE).babies.map {
                            it.id
                        }
                    )
                }
                assertEquals(listOf(489), tools.pair(game, 490, 132, ParentSex.GENDERLESS).babies.map { it.id })
                assertEquals(listOf(489), tools.pair(game, 489, 132, ParentSex.GENDERLESS).babies.map { it.id })
                assertEquals(listOf(314, 313), tools.pair(game, 314, 132, ParentSex.FEMALE).babies.map { it.id })
                assertEquals(listOf(29, 32), tools.pair(game, 29, 132, ParentSex.FEMALE).babies.map { it.id })
            }
        } finally {
            database.close()
        }
    }
}
