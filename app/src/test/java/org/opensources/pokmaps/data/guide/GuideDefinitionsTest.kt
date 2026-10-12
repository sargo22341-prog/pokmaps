package org.opensources.pokmaps.data.guide

import org.junit.Assert.assertEquals
import org.junit.Test

class GuideDefinitionsTest {
    private fun allDefinitions(): List<GuideDefinition> =
        kantoGuides() + johtoGuides() + sideGuides() + tipGuides() + gbaToolGuides() +
            hoennGuides() + hoennCalendarGuides() + hoennContentGuides() + remakeGuides() +
            (7..11).flatMap(::gbaCollectionGuides) + (1..11).flatMap(::achievementGuides)

    @Test
    fun selectingProvidersKeepsEveryDefinitionAndItsOrderForElevenGames() {
        val original = allDefinitions()
        for (version in 1..11) {
            assertEquals(original.filter { version in it.versions }, guideDefinitions(version))
        }
    }

    @Test(expected = IllegalStateException::class)
    fun unknownVersionHasNoImplicitLibrary() {
        guideDefinitions(12)
    }
}
