package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Test

class GuideTest {
    @Test
    fun linksPreserveEveryCharacterAndParagraph() {
        val parsed =
            parseGuideText("Voir [[pokemon:25|Pikachu]], puis [[place:route-1|Route 1]].\n\nFin.") { kind, value ->
                if (kind == "pokemon") GuideTarget.Pokemon(value.toInt()) else GuideTarget.Place(value)
            }
        assertEquals(
            listOf("Voir Pikachu, puis Route 1.", "Fin."),
            parsed.map {
                it.joinToString("") { span -> span.text }
            }
        )
        assertEquals(GuideTarget.Pokemon(25), parsed.first()[1].target)
        assertEquals(GuideTarget.Place("route-1"), parsed.first()[3].target)
    }

    @Test(expected = IllegalArgumentException::class)
    fun incompleteLinkFailsAtTheBoundary() {
        parseGuideText("[[pokemon:25|Pikachu") { _, _ -> GuideTarget.Pokemon(25) }
    }

    @Test(expected = IllegalArgumentException::class)
    fun duplicateRoamerInAnImportFails() {
        CollectionBackup(
            emptySet(),
            emptyMap(),
            mapOf(
                4 to GuideProgress(
                    roamers = listOf(
                        RoamerObservation(243, "route-29"),
                        RoamerObservation(243, "route-30")
                    )
                )
            )
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun crystalSuicuneDoesNotRoam() {
        validateGuideProgress(6, GuideProgress(roamers = listOf(RoamerObservation(245, "route-29"))))
    }
}
