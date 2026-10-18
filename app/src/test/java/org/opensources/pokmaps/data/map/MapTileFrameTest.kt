package org.opensources.pokmaps.data.map

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import java.io.ByteArrayInputStream
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.map.MapFrame
import org.opensources.pokmaps.domain.model.GameMap
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class MapTileFrameTest {
    private val house = GameMap(1, "header-twinleaf-town-rival-house-1f", "Maison", "platinum", 512, 512, 2)

    @Test
    fun sinnohHouseFrameExcludesTheTransparentMatrixMargins() = runTest {
        val context: Context = ApplicationProvider.getApplicationContext()
        val frame = mapTileFrame(AssetManagerFiles(context.assets), house)
        assertEquals(MapFrame(16.0 / 512, 4.0 / 512, 192.0 / 512, 180.0 / 512), frame)
    }

    @Test
    fun absentPreviewKeepsTheFullFrame() = runTest {
        assertEquals(MapFrame.FULL, mapTileFrame(AssetFiles { null }, house))
    }

    @Test
    fun invalidPreviewFailsRatherThanBeingTreatedAsAnEmptyMap() {
        assertThrows(IllegalArgumentException::class.java) {
            runTest { mapTileFrame(AssetFiles { ByteArrayInputStream(byteArrayOf(1, 2)) }, house) }
        }
    }
}
