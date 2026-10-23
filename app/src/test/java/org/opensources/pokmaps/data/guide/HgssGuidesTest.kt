package org.opensources.pokmaps.data.guide

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.guide.parseGuideText
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class HgssGuidesTest {
    @Test
    fun bothVersionsLoadTheirWalkthroughObjectivesAndConditionalCatalogs() {
        val resources = ApplicationProvider.getApplicationContext<Context>().resources
        for (game in listOf(FakeGameDao.HEARTGOLD, FakeGameDao.SOULSILVER)) {
            val definitions = guideDefinitions(game, resources)
            assertTrue(definitions.size + 136 <= 500)
            assertEquals(definitions.size, definitions.map { it.id }.toSet().size)
            assertEquals(54, definitions.count { it.captureGoal != null })
            assertTrue(definitions.any { it.category == GuideCategory.WALKTHROUGH })
            assertTrue(definitions.any { it.id == "hgss-weekly-calendar" })
            assertEquals(60, definitions.count { it.id.startsWith("hgss-safari-") })
            assertEquals(27, definitions.count { it.id.startsWith("hgss-walker-") })
            for (entry in definitions) {
                assertEquals(setOf(game.versionId), entry.versions)
                assertFalse(resources.getString(entry.title).isBlank())
                val paragraphs = parseGuideText(resources.getString(entry.text)) { kind, value ->
                    when (kind) {
                        "pokemon" -> GuideTarget.Pokemon(value.toInt())
                        "place" -> GuideTarget.Place(value)
                        else -> error("Lien HGSS inattendu : $kind")
                    }
                }
                assertTrue(paragraphs.isNotEmpty())
                assertTrue(entry.relatedIds.all { id -> definitions.any { it.id == id } })
            }
        }
    }

    @Test
    fun starterConfigurationsKeepTheirSeparateCaptureGoals() {
        val resources = ApplicationProvider.getApplicationContext<Context>().resources
        val definitions = guideDefinitions(FakeGameDao.HEARTGOLD, resources)
        val national = definitions.filter { it.id.startsWith("hgss-goal-") && it.id.endsWith("-national") }
        assertEquals(27, national.size)
        for (definition in national) {
            val goal = requireNotNull(definition.captureGoal)
            assertEquals(1, goal.species.count { it in setOf(152, 155, 158) })
            assertEquals(1, goal.species.count { it in setOf(1, 4, 7) })
            assertEquals(1, goal.species.count { it in setOf(252, 255, 258) })
            assertTrue(goal.species.none { it in setOf(381, 383, 384, 483, 484, 487, 492, 493) })
        }
    }
}
