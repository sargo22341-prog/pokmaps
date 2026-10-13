package org.opensources.pokmaps.data.guide

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao

class GuideDefinitionsTest {
    private fun allDefinitions(): List<GuideDefinition> =
        kantoGuides() + johtoGuides() + sideGuides() + tipGuides() + gbaToolGuides() +
            hoennGuides() + hoennCalendarGuides() + hoennContentGuides() + remakeGuides() +
            (7..11).flatMap(::gbaCollectionGuides) + (1..11).flatMap(::achievementGuides)

    @Test
    fun selectingProvidersKeepsEveryDefinitionAndItsOrderForElevenGames() {
        val original = allDefinitions()
        assertEquals((1..11).toList(), FakeGameDao.ELEVEN_GAMES.map { it.versionId })
        for (game in FakeGameDao.ELEVEN_GAMES) {
            assertEquals(original.filter { game.versionId in it.versions }, guideDefinitions(game))
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
