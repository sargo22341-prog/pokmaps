package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toPixelMap
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.EncounterHabitat
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class EncounterLandscapeClippingTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun repeatedGroundDoesNotPaintTheFollowingSection() {
        // Cette couleur témoin est absente des textures et révèle tout débordement du décor.
        compose.setContent {
            Column(Modifier.width(300.dp).background(Color.Magenta)) {
                Box(Modifier.testTag("water")) {
                    EncounterWaterZone(EncounterHabitat.GRASS) { Text("Pokémon") }
                }
                Spacer(Modifier.fillMaxWidth().height(128.dp).testTag("following-section"))
            }
        }
        compose.waitUntil(timeoutMillis = 5_000) {
            val pixel = compose.onNodeWithTag("water").captureToImage().toPixelMap()[2, 2]
            pixel.alpha > 0f && pixel != Color.Magenta
        }
        val following = compose.onNodeWithTag("following-section").captureToImage().toPixelMap()
        assertEquals(Color.Magenta, following[following.width / 2, 2])
    }
}
