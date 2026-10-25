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
        val dimensions = mapOf(
            "maps/red-blue/sprites/beauty.webp" to IntSize(16, 16),
            "maps/ruby-sapphire/sprites/obj-event-gfx-beauty.webp" to IntSize(16, 32),
            "maps/emerald/sprites/obj-event-gfx-beauty.webp" to IntSize(16, 32),
            "maps/firered-leafgreen/sprites/obj-event-gfx-beauty.webp" to IntSize(16, 32),
            "maps/firered-leafgreen/sprites/obj-event-gfx-biker.webp" to IntSize(32, 32),
            "maps/emerald/sprites/obj-event-gfx-prof-birch.webp" to IntSize(16, 32),
            "maps/emerald/sprites/obj-event-gfx-mart-employee.webp" to IntSize(16, 32)
        )
        val sizes = mutableMapOf<String, IntSize>()
        compose.setContent {
            // Le zoom ne doit pas réduire les derniers sprites pour les faire tenir dans l'écran de test.
            Column(Modifier.wrapContentHeight(unbounded = true)) {
                dimensions.keys.forEach { path ->
                    MapSprite(path, null, zoom.value, Modifier.onSizeChanged { sizes[path] = it })
                }
            }
        }
        compose.waitUntil(10_000) {
            // Le chargement des images doit pouvoir déclencher la recomposition et la mesure suivantes.
            compose.mainClock.advanceTimeByFrame()
            dimensions.all { (path, source) -> sizes[path] == IntSize(source.width * 2, source.height * 2) }
        }
        compose.runOnIdle {
            dimensions.forEach { (path, source) ->
                assertEquals(IntSize(source.width * 2, source.height * 2), sizes[path])
            }
            zoom.value = 3f
        }
        compose.waitForIdle()
        compose.runOnIdle {
            dimensions.forEach { (path, source) ->
                assertEquals(IntSize(source.width * 3, source.height * 3), sizes[path])
            }
        }
    }
}
