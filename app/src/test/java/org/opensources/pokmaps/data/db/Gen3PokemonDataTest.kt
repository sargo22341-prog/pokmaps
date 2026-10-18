package org.opensources.pokmaps.data.db

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** Requêtes Room sur les deux branches GBA activées dans la base distribuée. */
@RunWith(RobolectricTestRunner::class)
class Gen3PokemonDataTest {
    private lateinit var database: PokedexDatabase

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.databaseBuilder(context, PokedexDatabase::class.java, "gen3-pokemon-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .allowMainThreadQueries()
            .build()
    }

    @After
    fun tearDown() {
        if (::database.isInitialized) database.close()
    }

    @Test
    fun regionalDexPrecedesNationalDexForBothBranches() = runBlocking {
        val dao = database.pokedexDao()
        assertEquals(listOf(4, 1), dao.catalogs(5).map { it.id })
        assertEquals(listOf(4, 1), dao.catalogs(6).map { it.id })
        assertEquals(listOf(2, 1), dao.catalogs(7).map { it.id })
        assertEquals(202, dao.pokedex(6, 4).size)
        assertEquals(386, dao.pokedex(6, 1).size)
        // Le National est partagé avec Sinnoh : la requête doit conserver la limite propre à chaque génération.
        assertEquals(493, dao.pokedex(8, 1).size)
        assertEquals(493, dao.pokedex(9, 1).size)
        assertEquals(151, dao.pokedex(8, 5).size)
        assertEquals(210, dao.pokedex(9, 6).size)
        assertEquals(156, dao.pokedex(6, 4).single { it.pokemonId == 25 }.number)
        assertTrue(dao.pokedex(6, 2).isEmpty())
    }

    @Test
    fun pokemonPageUsesRegionalNumberAndFallsBackToNational() = runBlocking {
        val dao = database.pokemonDao()
        assertEquals(156, dao.number(25, 6))
        assertEquals(133, dao.number(133, 6))
        assertEquals(25, dao.number(25, 7))
    }

    @Test
    fun abilitiesKeepBothSlotsAndFrenchGameDescriptions() = runBlocking {
        val dao = database.pokemonDao()
        for (group in 5..6) {
            val abilities = dao.abilities(282, 3, group)
            assertEquals(listOf("Synchro", "Calque"), abilities.map { it.name })
            assertTrue(abilities.all { !it.hidden && !it.description.isNullOrBlank() })
        }
        assertEquals(
            listOf(
                AbilityRow("Synchro", "Transfère statuts.", false),
                AbilityRow("Calque", "Imite la capacité spéciale.", false)
            ),
            dao.abilities(282, 3, 7)
        )
        assertTrue(dao.abilities(282, 2, 3).isEmpty())
    }
}
