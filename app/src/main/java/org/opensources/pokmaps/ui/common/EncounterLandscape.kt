package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import coil3.compose.rememberAsyncImagePainter
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.EncounterHabitat
import org.opensources.pokmaps.domain.model.Sprites

@Composable
internal fun EncounterLandSection(
    habitat: EncounterHabitat,
    enabled: Boolean = true,
    content: @Composable ColumnScope.() -> Unit
) {
    if (!enabled) {
        Column(content = content)
        return
    }
    Box(Modifier.fillMaxWidth()) {
        LandscapeTexture(habitat, lake = false, Modifier.matchParentSize())
        LandscapeBoundary()
        Surface(
            color = MaterialTheme.colorScheme.surface.copy(alpha = 0.72f),
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 16.dp)
        ) {
            Column(Modifier.fillMaxWidth().padding(8.dp), content = content)
        }
    }
}

@Composable
internal fun EncounterWaterZone(habitat: EncounterHabitat, content: @Composable ColumnScope.() -> Unit) {
    Box(Modifier.fillMaxWidth()) {
        LandscapeTexture(habitat, lake = false, Modifier.matchParentSize())
        LandscapeBoundary()
        LandscapeTexture(habitat, lake = true, Modifier.matchParentSize().padding(top = 16.dp, bottom = 8.dp))
        Column(
            Modifier.padding(horizontal = 16.dp, vertical = 40.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Surface(
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.88f),
                shape = MaterialTheme.shapes.small
            ) {
                Text(
                    stringResource(R.string.water_zone),
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                )
            }
            content()
        }
    }
}

@Composable
internal fun EncounterWaterCard(
    habitat: EncounterHabitat,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    Box(modifier.clip(MaterialTheme.shapes.medium)) {
        // Seul le décor est flouté : noms, icônes et probabilités restent nets.
        LandscapeTexture(habitat, lake = true, Modifier.matchParentSize().blur(8.dp))
        Surface(
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.surface.copy(alpha = 0.68f),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.6f)),
            content = content
        )
    }
}

@Composable
private fun LandscapeTexture(habitat: EncounterHabitat, lake: Boolean, modifier: Modifier) {
    val kind = if (lake) "lake" else "ground"
    val forest = habitat == EncounterHabitat.FOREST && !lake
    val asset = if (forest) {
        "maps/emerald/petalburg-woods/2/0_0.webp"
    } else {
        "encounter_backgrounds/${habitat.asset}_$kind.webp"
    }
    val painter = rememberAsyncImagePainter(
        model = Sprites.assetUri(asset),
        filterQuality = FilterQuality.None
    )
    Canvas(modifier.clipToBounds()) {
        if (lake) {
            drawLake(painter, 32.dp.toPx())
        } else {
            val step = 128.dp.toPx()
            val columns = (size.width / step).toInt().coerceIn(0, 31) + 1
            val rows = (size.height / step).toInt().coerceIn(0, 511) + 1
            for (row in 0 until rows) {
                for (column in 0 until columns) {
                    withTransform({ translate(column * step, row * step) }) {
                        clipRect(0f, 0f, step, step) {
                            val scale = if (forest) 4f else 1f
                            with(painter) { draw(Size(step * scale, step * scale)) }
                        }
                    }
                }
            }
        }
    }
}

private fun DrawScope.drawLake(painter: Painter, edge: Float) {
    drawLakeCell(painter, 1, 1, 0f, 0f, size.width, size.height)
    val columns = (size.width / edge).toInt().coerceIn(0, 127) + 1
    val rows = (size.height / edge).toInt().coerceIn(0, 511) + 1
    clipRect(edge, 0f, (size.width - edge).coerceAtLeast(edge), size.height) {
        for (column in 0 until columns) {
            drawLakeCell(painter, 1, 0, column * edge, 0f, edge, edge)
            drawLakeCell(painter, 1, 2, column * edge, size.height - edge, edge, edge)
        }
    }
    clipRect(0f, edge, size.width, (size.height - edge).coerceAtLeast(edge)) {
        for (row in 0 until rows) {
            drawLakeCell(painter, 0, 1, 0f, row * edge, edge, edge)
            drawLakeCell(painter, 2, 1, size.width - edge, row * edge, edge, edge)
        }
    }
    drawLakeCell(painter, 0, 0, 0f, 0f, edge, edge)
    drawLakeCell(painter, 2, 0, size.width - edge, 0f, edge, edge)
    drawLakeCell(painter, 0, 2, 0f, size.height - edge, edge, edge)
    drawLakeCell(painter, 2, 2, size.width - edge, size.height - edge, edge, edge)
}

private fun DrawScope.drawLakeCell(
    painter: Painter,
    column: Int,
    row: Int,
    left: Float,
    top: Float,
    width: Float,
    height: Float
) {
    clipRect(left, top, left + width, top + height) {
        withTransform({ translate(left - column * width, top - row * height) }) {
            with(painter) { draw(Size(width * 3f, height * 3f)) }
        }
    }
}

@Composable
internal fun LandscapeBoundary() {
    val edge = MaterialTheme.colorScheme.scrim.copy(alpha = 0.28f)
    Canvas(Modifier.fillMaxWidth().height(12.dp)) {
        drawRect(Brush.verticalGradient(listOf(edge, Color.Transparent)))
    }
}
