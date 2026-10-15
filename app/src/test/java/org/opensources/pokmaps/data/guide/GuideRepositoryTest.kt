package org.opensources.pokmaps.data.guide

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.repository.HoennRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.Game
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class GuideRepositoryTest {
    @Test
    fun elevenLibrariesResolveEveryLinkAndKeepAllOfficialAchievements() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "guides-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        try {
            val maps = MapRepository(database.mapDao(), Dispatchers.Unconfined)
            val repository =
                GuideRepository(context, maps, PokedexRepository(database.pokedexDao()), HoennRepository(context))
            val expected = listOf(93, 90, 76, 72, 75, 113)
            for (game in database.gameDao().games().first()) {
                val library = repository.library(game)
                if (game.generationId == 3) {
                    checkGbaArticles(library)
                    val itemIds = maps.index(game).items.map { it.identifier }.toSet()
                    val itemLinks = library.articles.flatMap { it.paragraphs.flatten() }
                        .mapNotNull { it.target as? GuideTarget.Item }
                    assertTrue(itemLinks.all { it.identifier in itemIds })
                    checkFruitSprites(context, maps.catalog(game), game)
                    continue
                }
                checkSeparateQuests(library)
                checkFruitSprites(context, maps.catalog(game), game)
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

    private fun checkGbaArticles(library: org.opensources.pokmaps.domain.guide.GuideLibrary) {
        val achievements = library.articles.filter { it.achievementId != null }
        val expectedCounts = mapOf(7 to 49, 8 to 49, 9 to 197, 10 to 61, 11 to 128)
        assertEquals(expectedCounts[library.game.versionId], achievements.size)
        assertTrue(achievements.all { it.points > 0 && it.sources.single().endsWith("/${it.achievementId}") })
        val articles = library.articles.filter { it.achievementId == null }
        val hoenn = library.game.versionId in 7..9
        val mascot = if (hoenn) 252 else 25
        assertTrue(achievements.all { it.pokemonId == mascot })
        if (hoenn) {
            val links = library.articles.flatMap { it.paragraphs.flatten() }
                .filter { it.target is GuideTarget.Character }.map { it.text }.toSet()
            assertTrue(links.containsAll(setOf("Roxanne", "Voltère", "Damien", "Spectra", "Glacia", "Aragon")))
        }
        val prefix = if (hoenn) "hoenn-" else "remake-"
        // Sans les deux collections GBA, avec l'article des errants et, à Hoenn, celui des Bases Secrètes.
        assertEquals(if (hoenn) 31 else 19, articles.size)
        assertEquals(articles.size, articles.map { it.id }.distinct().size)
        assertTrue(articles.all { it.id in setOf("breeding", "friendship") || it.id.startsWith(prefix) })
        assertTrue(articles.all { it.paragraphs.size >= 3 && it.sources.isNotEmpty() && it.title.isNotBlank() })
        assertEquals(12, articles.count { it.category == GuideCategory.WALKTHROUGH })
        assertTrue(articles.none { it.category == GuideCategory.ACHIEVEMENT })
        val expected = GuideCategory.entries.toSet() - GuideCategory.ACHIEVEMENT -
            if (hoenn) emptySet() else setOf(GuideCategory.CALENDAR)
        assertEquals(expected, articles.map { it.category }.toSet())
        val targets = articles.flatMap { it.paragraphs.flatten() }.mapNotNull { it.target }
        assertTrue(targets.any { it is GuideTarget.Pokemon })
        assertTrue(targets.any { it is GuideTarget.Place })
        if (hoenn) {
            assertEquals(4, articles.count { it.category == GuideCategory.CALENDAR })
            assertEquals(GuideCategory.SIDE_QUEST, articles.single { it.id == "hoenn-trick-house" }.category)
            assertTrue(articles.single { it.id == "hoenn-tides" }.summary.contains("9 h à 14 h 59"))
            val bases = articles.single { it.id == "hoenn-secret-bases" }
            assertEquals(GuideCategory.TIP, bases.category)
            assertTrue(bases.summary.contains("Les 75 emplacements du jeu"))
            // Les espaces autour des séparateurs ne sont pas retirés par les ressources Android.
            assertTrue(bases.summary, bases.summary.contains("Route 110 (2) : Base Secrète (arbre 3) · Base"))
            val decorations = articles.single { it.id == "hoenn-decorations" }.summary
            assertTrue(decorations.contains("Achat ou échange (") && decorations.contains(") : "))
            assertTrue(!decorations.contains("récompense :") || decorations.contains("récompense : "))
            assertEquals(75, bases.paragraphs.flatten().count { it.target is GuideTarget.SecretBase })
        } else {
            assertTrue(articles.single { it.id == "remake-collections" }.unownGoal)
            assertTrue(articles.single { it.id == "remake-sapphire" }.summary.contains("Entei avec Bulbizarre"))
            assertTrue(articles.single { it.id == "remake-sapphire" }.summary.contains("Raikou avec Carapuce"))
            assertTrue(articles.single { it.id == "remake-sapphire" }.summary.contains("Suicune avec Salamèche"))
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
        game: Game
    ) {
        val trees = catalog.objects.values.flatten().filter { it.fruit != null }
        if (game.generationId == 1 || game.remakeGenerationId == 1) {
            assertTrue(trees.isEmpty())
            return
        }
        assertTrue(trees.isNotEmpty())
        if (game.mapFamily == "ruby-sapphire-emerald") assertEquals(81, trees.size)
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
