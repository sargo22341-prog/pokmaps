package org.opensources.pokmaps.data.repository

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.EvolutionGender
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.robolectric.RobolectricTestRunner

/** Requêtes DS sur la base distribuée : aucun cache ni réseau pendant les tests. */
@RunWith(RobolectricTestRunner::class)
class Gen4PokemonRepositoryTest {
    private lateinit var database: PokedexDatabase
    private lateinit var pokemon: PokemonRepository
    private lateinit var pokedex: PokedexRepository
    private lateinit var games: List<Game>

    @Before
    fun setUp() = runBlocking {
        database = Room.databaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(),
            PokedexDatabase::class.java,
            "gen4-test.db"
        ).createFromFile(File(requireNotNull(System.getProperty("pokemaps.database")))).build()
        pokedex = PokedexRepository(database.pokedexDao())
        pokemon = PokemonRepository(database.pokemonDao(), pokedex)
        games = database.gameDao().games().first().filter { it.versionId in 12..14 }
    }

    @After
    fun tearDown() = database.close()

    @Test
    fun sinnohPrecedesNationalAndSheetsKeepBothNumbers() = runBlocking {
        for (game in games) {
            assertEquals(listOf(if (game.versionId == 14) 6 else 5, 1), pokedex.catalogs(game).map { it.id })
            val regional = pokedex.pokedex(game)
            assertEquals(387, regional.first().pokemonId)
            assertTrue(regional.none { it.pokemonId == 493 })
            assertTrue(pokedex.pokedex(game, 1).any { it.pokemonId == 493 })
            val starter = checkNotNull(pokemon.details(game, 387))
            assertEquals(1, starter.number)
            assertEquals(1, starter.regionalNumber)
            val national = checkNotNull(pokemon.details(game, 493))
            assertEquals(493, national.number)
            assertNull(national.regionalNumber)
            val leafeon = checkNotNull(pokemon.details(game, 470))
            assertEquals(if (game.versionId == 14) 169 else 470, leafeon.number)
            assertEquals(if (game.versionId == 14) 169 else null, leafeon.regionalNumber)
        }
    }

    @Test
    fun damageClassBelongsToTheMoveRatherThanItsType() = runBlocking {
        val moves = MoveRepository(database.moveDao(), HoennRepository { error("Hors Hoenn") })
        assertEquals("special", database.moveDao().move(9, 5)?.damageClass)
        assertEquals("physical", database.moveDao().move(247, 5)?.damageClass)
        for (game in games) {
            assertEquals(DamageClass.PHYSICAL, moves.details(game, 9)?.damageClass)
            assertEquals(DamageClass.SPECIAL, moves.details(game, 247)?.damageClass)
        }
    }

    @Test
    fun evolutionRequirementsSurviveTheDatabaseAndDomainConversion() = runBlocking {
        for (game in games) {
            val eevee = checkNotNull(pokemon.details(game, 133)).evolutions.single { it.pokemonId == 133 }
            assertTrue(eevee.children.single { it.pokemonId == 470 }.condition?.nearSpecialRock == true)
            assertEquals("Forêt Vestigion", eevee.children.single { it.pokemonId == 470 }.condition?.locationName)
            val burmy = checkNotNull(pokemon.details(game, 412)).evolutions.single()
            val cloaks = burmy.children.filter { it.pokemonId == 413 }.map { checkNotNull(it.condition) }
            assertEquals(3, cloaks.size)
            assertTrue(cloaks.all { it.gender == EvolutionGender.FEMALE })
            assertEquals(setOf("Cape Plante", "Cape Sable", "Cape Déchet"), cloaks.map { it.requiredFormName }.toSet())
            assertEquals(
                setOf("plant", "sandy", "trash"),
                cloaks.map { checkNotNull(it.evolvedForm).spriteIdentifier }.toSet()
            )
            val mantyke = checkNotNull(pokemon.details(game, 458)).evolutions.single()
            assertEquals("Rémoraid", mantyke.children.single().condition?.partySpeciesName)
            val sneasel = database.pokemonDao().evolutions(109, game.versionGroupId)
            assertTrue(sneasel.any { it.heldItem && it.timeOfDay == "night" })
            val tangela = database.pokemonDao().evolutions(52, game.versionGroupId)
            assertEquals("Pouvoir Antique", tangela.single().knownMoveName)
        }
    }

    @Test
    fun retainedFormsFollowTheCartridgeAndUnownHas28Letters() {
        for (game in games) {
            assertEquals(28, UnownForm.available(game).size)
            assertEquals(if (game.versionId == 14) 6 else 1, game.forms.getValue(479).size)
            assertEquals(if (game.versionId == 14) 2 else 1, game.forms.getValue(487).size)
            for (form in game.forms.values.flatten()) {
                assertTrue(form.sprite(animated = true, shiny = true).contains("/shiny/animated/"))
            }
        }
    }
}
