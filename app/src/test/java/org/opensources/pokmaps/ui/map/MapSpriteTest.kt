package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.unit.IntSize
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class MapSpriteTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun gbaSpritesKeepTheirNativeDimensionsAndFollowZoom() {
        val zoom = mutableStateOf(2f)
        val paths = listOf(
            "maps/red-blue/sprites/beauty.webp",
            "maps/ruby-sapphire/sprites/obj-event-gfx-beauty.webp",
            "maps/emerald/sprites/obj-event-gfx-beauty.webp",
            "maps/firered-leafgreen/sprites/obj-event-gfx-beauty.webp",
            "maps/firered-leafgreen/sprites/obj-event-gfx-biker.webp"
        )
        val sizes = mutableMapOf<String, IntSize>()
        compose.setContent {
            // Le zoom ne doit pas réduire les derniers sprites pour les faire tenir dans l'écran de test.
            Column(Modifier.wrapContentHeight(unbounded = true)) {
                paths.forEach { path ->
                    MapSprite(path, null, zoom.value, Modifier.onSizeChanged { sizes[path] = it })
                }
            }
        }
        compose.waitUntil(10_000) {
            paths.subList(1, 4).all { sizes[it] == IntSize(32, 64) } && sizes[paths[4]] == IntSize(64, 64)
        }
        compose.runOnIdle {
            assertEquals(IntSize(32, 32), sizes[paths[0]])
            paths.subList(1, 4).forEach { assertEquals(IntSize(32, 64), sizes[it]) }
            assertEquals(IntSize(64, 64), sizes[paths[4]])
            zoom.value = 3f
        }
        compose.waitForIdle()
        compose.runOnIdle {
            assertEquals(IntSize(48, 48), sizes[paths[0]])
            paths.subList(1, 4).forEach { assertEquals(IntSize(48, 96), sizes[it]) }
            assertEquals(IntSize(96, 96), sizes[paths[4]])
        }
    }
}
