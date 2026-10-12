package org.opensources.pokmaps.data.repository

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.usecase.ObservePokemonUseCase
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PokemonRepositoryTest {
    private lateinit var database: PokedexDatabase
    private lateinit var repository: PokemonRepository

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.databaseBuilder(context, PokedexDatabase::class.java, "pokemon-repository-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        repository = PokemonRepository(database.pokemonDao(), PokedexRepository(database.pokedexDao()))
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun evolutionRootsRespectTheGenerationWithoutRestrictingToTheRegionalDex() = runBlocking {
        for (game in listOf(FakeGameDao.RED, FakeGameDao.BLUE)) {
            assertEquals(listOf(25), roots(game, 25))
        }
        val gold = FakeGameDao.GOLD
        val silver = gold.copy(versionId = 5, versionIdentifier = "silver")
        for (game in listOf(gold, silver)) {
            assertEquals(listOf(172), roots(game, 25))
            assertEquals(listOf(183), roots(game, 183))
            assertEquals(listOf(202), roots(game, 202))
        }
        for (game in FakeGameDao.GBA_GAMES) {
            assertEquals(listOf(172), roots(game, 25))
            assertEquals(listOf(298), roots(game, 183))
            assertEquals(listOf(360), roots(game, 202))
        }
    }

    @Test
    fun futureSpeciesAreAbsentButNationalSpeciesOutsideTheRegionHaveACompleteSheet() = runBlocking {
        assertNull(repository.details(FakeGameDao.RED, 252))
        assertNull(repository.details(FakeGameDao.GOLD, 298))
        val chikorita = checkNotNull(repository.details(FakeGameDao.RUBY, 152))
        assertNotNull(chikorita.number)
        assertEquals(listOf("grass"), chikorita.types.map { it.identifier })
        assertEquals(6, chikorita.stats.size)
        assertTrue(chikorita.encounters.none { it.versionId == FakeGameDao.RUBY.versionId })
    }

    @Test
    fun aBlockedEvolutionKeepsHistoricalMembersWithoutInventingALink() = runBlocking {
        val delegate = database.pokemonDao()
        val dao = object : PokemonDao by delegate {
            override suspend fun evolutions(chainId: Int, versionGroupId: Int) =
                delegate.evolutions(chainId, versionGroupId).filterNot { it.toId == 26 }
        }
        val pokemon = PokemonRepository(dao, PokedexRepository(database.pokedexDao()))
        val family = checkNotNull(pokemon.details(FakeGameDao.RED, 25)).evolutions
        assertEquals(listOf(25, 26), family.map { it.pokemonId })
        assertTrue(family.all { it.children.isEmpty() })
    }

    @Test
    fun changingFromRubyToRedMakesATreeckoSheetAbsent() = runBlocking {
        val games = GameRepository(
            FakeGameDao(listOf(FakeGameDao.RUBY, FakeGameDao.RED)),
            GameSettings(FakeDataStore())
        )
        val pages = withTimeout(10_000) {
            ObservePokemonUseCase(games, repository)(252).onEach {
                if (it.game == FakeGameDao.RUBY) games.select(FakeGameDao.RED)
            }.take(2).toList()
        }
        assertEquals(listOf(FakeGameDao.RUBY, FakeGameDao.RED), pages.map { it.game })
        assertNotNull(pages.first().details)
        assertNull(pages.last().details)
    }

    private suspend fun roots(game: Game, pokemonId: Int): List<Int> =
        checkNotNull(repository.details(game, pokemonId)).evolutions.map { it.pokemonId }
}
