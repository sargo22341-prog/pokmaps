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

/** Requêtes Room sur une copie de la base, enrichie avec des données GBA des sources épinglées. */
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
        val sql = database.openHelper.writableDatabase
        sql.execSQL("INSERT INTO pokedex VALUES (1, 'national', 'National', NULL), (4, 'hoenn', 'Hoenn', 3)")
        sql.execSQL("INSERT INTO version_group_pokedex VALUES (5, 4), (5, 1), (6, 4), (6, 1), (7, 2), (7, 1)")
        sql.execSQL("INSERT INTO pokedex_entry VALUES (4, 25, 156), (1, 25, 25), (1, 133, 133)")
        seedAbilities()
    }

    private fun seedAbilities() {
        val sql = database.openHelper.writableDatabase
        sql.execSQL("INSERT INTO ability VALUES (28, 'synchronize', 'Synchro', 3), (36, 'trace', 'Calque', 3)")
        sql.execSQL("INSERT INTO pokemon_ability VALUES (282, 3, 1, 28, 0), (282, 3, 2, 36, 0)")
        for (group in 5..7) {
            sql.execSQL(
                "INSERT INTO ability_version_group VALUES (?, ?, ?), (?, ?, ?)",
                arrayOf<Any>(28, group, "Transfère statuts.", 36, group, "Imite la capacité spéciale.")
            )
        }
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
        assertEquals(listOf(156), dao.pokedex(6, 4).map { it.number })
        assertEquals(listOf(25, 133), dao.pokedex(6, 1).map { it.number })
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
        for (group in 5..7) {
            assertEquals(
                listOf(
                    AbilityRow("Synchro", "Transfère statuts.", false),
                    AbilityRow("Calque", "Imite la capacité spéciale.", false)
                ),
                dao.abilities(282, 3, group)
            )
        }
        assertTrue(dao.abilities(282, 2, 3).isEmpty())
    }
}
