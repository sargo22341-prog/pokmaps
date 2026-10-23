package org.opensources.pokmaps.data.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.R
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.Roamers

class GuideDefinitionsTest {
    private fun allDefinitions(): List<GuideDefinition> =
        kantoGuides() + johtoGuides() + sideGuides() + tipGuides() + gbaToolGuides() +
            hoennGuides() + hoennCalendarGuides() + hoennContentGuides() + remakeGuides()

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

    @Test
    fun sinnohDoesNotInheritTheGbaTools() {
        listOf(FakeGameDao.DIAMOND, FakeGameDao.PEARL, FakeGameDao.PLATINUM).forEach {
            val articles = guideDefinitions(it)
            assertEquals(33, articles.size)
            assertEquals(R.string.guide_breeding_sinnoh_text, articles.single { a -> a.id == "breeding" }.text)
            assertEquals(R.string.guide_friendship_sinnoh_text, articles.single { a -> a.id == "friendship" }.text)
            assertTrue(articles.all { article -> article.versions == setOf(it.versionId) })
            val contentIds = setOf(
                "sinnoh-berries",
                "sinnoh-super-contests",
                "sinnoh-poffins",
                "sinnoh-underground",
                "sinnoh-battle"
            )
            val previous = articles.filter { article -> article.id !in contentIds }
            assertEquals(28, previous.size)
            assertTrue(previous.all { article -> article.sources == sinnohGuideSources(it) })
            val repo = if (it.versionId == 14) "pokeplatinum" else "pokediamond"
            assertTrue(
                articles.filter { article -> article.id in contentIds }.all { article ->
                    article.sources.all { source -> source.startsWith("https://github.com/pret/$repo/blob/") }
                }
            )
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownVersionOfAKnownGroupHasNoImplicitLibrary() {
        guideDefinitions(FakeGameDao.RED.copy(versionId = 17))
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownGroupHasNoImplicitLibrary() {
        guideDefinitions(FakeGameDao.EMERALD.copy(versionGroupIdentifier = "unsupported"))
    }

    @Test
    fun preparatoryHgssDoesNotBorrowGuidesFromAnotherBranch() {
        assertTrue(guideDefinitions(FakeGameDao.HEARTGOLD).isEmpty())
        assertTrue(guideDefinitions(FakeGameDao.SOULSILVER).isEmpty())
    }
}
