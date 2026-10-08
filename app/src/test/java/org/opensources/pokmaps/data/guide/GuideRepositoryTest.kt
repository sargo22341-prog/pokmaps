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
            val repository =
                GuideRepository(context, MapRepository(database.mapDao()), PokedexRepository(database.pokedexDao()))
            val expected = listOf(93, 90, 76, 72, 75, 113)
            for (game in database.gameDao().games().first()) {
                val library = repository.library(game)
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
}
