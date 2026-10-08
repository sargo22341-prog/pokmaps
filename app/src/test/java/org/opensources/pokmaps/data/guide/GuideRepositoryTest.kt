package org.opensources.pokmaps.data.guide

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
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class GuideRepositoryTest {
    @Test
    fun sixLibrariesResolveEveryLinkAndKeepAllOfficialAchievements() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "guides-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        try {
            val maps = MapRepository(database.mapDao())
            val repository = GuideRepository(context, maps, PokedexRepository(database.pokedexDao()))
            val expected = listOf(93, 90, 76, 72, 75, 113)
            for (game in database.gameDao().games().first()) {
                val library = repository.library(game)
                checkSeparateQuests(library)
                checkFruitSprites(context, maps.catalog(game), game.generationId)
                val achievements = library.articles.filter { it.category == GuideCategory.ACHIEVEMENT }
                assertEquals(expected[game.versionId - 1], achievements.size)
                val categories = GuideCategory.entries.toSet() -
                    if (game.generationId == 1) setOf(GuideCategory.CALENDAR) else emptySet()
                assertEquals(categories, library.articles.map { it.category }.toSet())
                assertTrue(library.articles.filter { it.category == GuideCategory.WALKTHROUGH }.size >= 12)
                assertTrue(achievements.all { it.achievementId != null && it.points > 0 })
                assertTrue(library.articles.all { it.paragraphs.isNotEmpty() && it.title.isNotBlank() })
                val targets = library.articles.flatMap { it.paragraphs.flatten() }.mapNotNull { it.target }
                assertTrue(targets.any { it is GuideTarget.Character })
                assertTrue(targets.any { it is GuideTarget.Pokemon })
                assertTrue(targets.any { it is GuideTarget.Item })
                assertTrue(targets.any { it is GuideTarget.Place })
            }
        } finally {
            database.close()
        }
    }

    private fun checkSeparateQuests(library: org.opensources.pokmaps.domain.guide.GuideLibrary) {
        val quests = library.articles.filter { it.category == GuideCategory.SIDE_QUEST }
        val ids = quests.map { it.id }.toSet()
        val expected = if (library.game.generationId == 1) {
            setOf("kanto-dojo", "kanto-fossils")
        } else {
            setOf("johto-legends", "johto-hooh", "johto-roamers")
        }
        assertTrue(ids.containsAll(expected))
        if (library.game.generationId == 2) {
            assertTrue(library.articles.single { it.id == "johto-mahogany" }.shiny)
            val lugia = quests.single { it.id == "johto-legends" }
            val hooh = quests.single { it.id == "johto-hooh" }
            assertEquals(249, lugia.pokemonId)
            assertEquals(250, hooh.pokemonId)
            assertTrue(lugia.paragraphs.flatten().none { it.target == GuideTarget.Pokemon(250) })
        }
    }

    private fun checkFruitSprites(
        context: Context,
        catalog: org.opensources.pokmaps.domain.map.MapCatalog,
        generation: Int
    ) {
        val trees = catalog.objects.values.flatten().filter { it.fruit != null }
        if (generation == 1) {
            assertTrue(trees.isEmpty())
            return
        }
        assertTrue(trees.isNotEmpty())
        trees.forEach { tree ->
            val fruit = requireNotNull(tree.fruit)
            assertEquals(
                org.opensources.pokmaps.domain.map.MapLayer.FRUIT_TREES,
                org.opensources.pokmaps.domain.map.MapLayer.of(tree)
            )
            context.assets.open(org.opensources.pokmaps.domain.model.Sprites.item(fruit.identifier)).use {
                assertTrue(it.read() >= 0)
            }
        }
    }
}
