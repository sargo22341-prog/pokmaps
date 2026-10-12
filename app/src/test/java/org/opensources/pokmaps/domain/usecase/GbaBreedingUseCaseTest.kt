package org.opensources.pokmaps.domain.usecase

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
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
class GbaBreedingUseCaseTest {
    @Test
    fun allFiveGamesUseNationalParentsAndKeepIncenseAndIllumiseAlternatives() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "gba-breeding-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        try {
            val pokedex = PokedexRepository(database.pokedexDao())
            val pokemon = PokemonRepository(database.pokemonDao(), pokedex)
            val games = database.gameDao().games().first().filter { it.generationId == 3 }
            assertEquals(5, games.size)
            for (game in games) {
                val tools = BreedingUseCase(
                    GameRepository(FakeGameDao(listOf(game)), GameSettings(FakeDataStore())),
                    pokedex,
                    pokemon
                )
                val catalog = tools.observe().first()
                assertEquals(386, catalog.pokemon.size)
                assertEquals(catalog.pokemon.map { it.pokemonId }.toSet(), catalog.profiles.keys)
                assertTrue(132 in catalog.profiles)
                assertEquals(listOf(298, 183), tools.pair(game, 183, 132, ParentSex.FEMALE).babies.map { it.id })
                assertEquals(listOf(360, 202), tools.pair(game, 202, 132, ParentSex.FEMALE).babies.map { it.id })
                assertEquals(listOf(314, 313), tools.pair(game, 314, 132, ParentSex.FEMALE).babies.map { it.id })
                assertEquals(3, tools.pair(game, 25, 132, ParentSex.FEMALE).generationId)
            }
        } finally {
            database.close()
        }
    }
}
