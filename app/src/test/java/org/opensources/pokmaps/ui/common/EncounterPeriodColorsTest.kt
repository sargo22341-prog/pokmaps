package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import kotlin.math.abs
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class EncounterPeriodColorsTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun unavailablePeriodsAreGrayAndAvailablePeriodKeepsItsOriginalColors() {
        compose.setContent {
            Box(Modifier.background(Color.White)) { EncounterTimeIcons(encounter(setOf(EncounterTime.MORNING))) }
        }
        assertTrue(isColored("Horaire de rencontre : Matin"))
        assertFalse(isColored("Horaire de rencontre : Jour : Indisponible"))
        assertFalse(isColored("Horaire de rencontre : Nuit : Indisponible"))
    }

    @Test
    fun untimedEncounterKeepsAllThreePeriodsColored() {
        compose.setContent { Box(Modifier.background(Color.White)) { EncounterTimeIcons(encounter(emptySet())) } }
        assertTrue(isColored("Horaire de rencontre : Matin"))
        assertTrue(isColored("Horaire de rencontre : Jour"))
        assertTrue(isColored("Horaire de rencontre : Nuit"))
    }

    private fun isColored(description: String): Boolean {
        val pixels = compose.onNodeWithContentDescription(description).captureToImage().toPixelMap()
        for (y in 0 until pixels.height) {
            for (x in 0 until pixels.width) {
                val color = pixels[x, y]
                if (abs(color.red - color.green) > 0.03f || abs(color.green - color.blue) > 0.03f) return true
            }
        }
        return false
    }

    private fun encounter(times: Set<EncounterTime>) = Encounter(
        4, "Or", 1, "Route", 16, "Roucool", "walk", "Marche", 1, false,
        2, 4, 30.0, 1, null, null, times
    )
}
