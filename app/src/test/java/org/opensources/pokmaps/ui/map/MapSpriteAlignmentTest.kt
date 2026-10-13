package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInRoot
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.toSize
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MapSpriteAlignmentTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun feetAndBadgeKeepTheSameTileAnchorForEverySpriteSize() {
        val sources = listOf(IntSize(16, 16), IntSize(16, 32), IntSize(32, 32))
        val frames = mutableMapOf<IntSize, Rect>()
        val images = mutableMapOf<IntSize, Rect>()
        compose.setContent {
            val density = LocalDensity.current
            sources.forEach { source ->
                Box(
                    Modifier
                        .onGloballyPositioned { frames[source] = bounds(it) }
                        .spriteTileFrame(2f)
                        .onGloballyPositioned { images[source] = bounds(it) }
                        .size(with(density) { (source.width * 2).toDp() }, with(density) { (source.height * 2).toDp() })
                )
            }
        }
        compose.runOnIdle {
            sources.forEach { source ->
                val frame = frames.getValue(source)
                val image = images.getValue(source)
                assertEquals(32f, frame.width)
                assertEquals(32f, frame.height)
                assertEquals(source.width * 2f, image.width)
                assertEquals(source.height * 2f, image.height)
                assertEquals(frame.center.x, image.center.x)
                assertEquals(frame.bottom, image.bottom)
            }
        }
    }

    private fun bounds(coordinates: LayoutCoordinates): Rect =
        Rect(coordinates.positionInRoot(), coordinates.size.toSize())
}
