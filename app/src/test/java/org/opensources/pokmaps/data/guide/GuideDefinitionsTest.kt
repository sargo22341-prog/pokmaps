package org.opensources.pokmaps.data.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.Roamers

class GuideDefinitionsTest {
    private fun allDefinitions(): List<GuideDefinition> =
        kantoGuides() + johtoGuides() + sideGuides() + tipGuides() + gbaToolGuides() +
            hoennGuides() + hoennCalendarGuides() + hoennContentGuides() + remakeGuides() +
            (1..11).flatMap(::achievementGuides)

    @Test
    fun selectingProvidersKeepsEveryDefinitionAndItsOrderForElevenGames() {
        val original = allDefinitions()
        assertEquals((1..11).toList(), FakeGameDao.ELEVEN_GAMES.map { it.versionId })
        for (game in FakeGameDao.ELEVEN_GAMES) {
            assertEquals(original.filter { game.versionId in it.versions }, guideDefinitions(game))
        }
    }

    @Test
    fun gbaGamesKeepTheirPokedexCounterWithoutDuplicateCollectionQuests() {
        for (game in FakeGameDao.ELEVEN_GAMES.filter { it.versionId >= 7 }) {
            val ids = guideDefinitions(game).map { it.id }
            assertTrue(ids.none { it.endsWith("regional-collection") || it.endsWith("national-collection") })
        }
    }

    @Test
    fun everyGameWithRoamersPresentsThemInASideQuest() {
        for (game in FakeGameDao.ELEVEN_GAMES.filter { it.versionId >= 4 }) {
            val article = guideDefinitions(game).single { it.id == Roamers.article(game.versionId) }
            assertEquals(GuideCategory.SIDE_QUEST, article.category)
        }
    }

    @Test
    fun ruinsOfAlphCountTheUnownAlphabetInGoldSilverAndCrystal() {
        for (game in FakeGameDao.ELEVEN_GAMES.filter { it.versionId in 4..6 }) {
            assertTrue(guideDefinitions(game).single { it.id == "johto-alph" }.unownGoal)
        }
    }

    @Test(expected = IllegalStateException::class)
    fun unknownVersionOfAKnownGroupHasNoImplicitLibrary() {
        guideDefinitions(FakeGameDao.RED.copy(versionId = 12))
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownGroupHasNoImplicitLibrary() {
        guideDefinitions(FakeGameDao.EMERALD.copy(versionGroupIdentifier = "diamond-pearl"))
    }
}
