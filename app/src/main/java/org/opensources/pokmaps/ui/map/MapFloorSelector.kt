package org.opensources.pokmaps.ui.map

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.FloorLevel
import org.opensources.pokmaps.domain.map.MapFloor

/** Étages du bâtiment ou de la grotte, de haut en bas, comme les boutons d'un ascenseur. */
@Composable
internal fun FloorSelector(floors: List<MapFloor>, currentId: Int?, onSelect: (Int) -> Unit) {
    Surface(shape = MaterialTheme.shapes.extraLarge, tonalElevation = 3.dp, shadowElevation = 2.dp) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .heightIn(max = FLOORS_MAX_HEIGHT)
                .verticalScroll(rememberScrollState())
                .padding(4.dp)
        ) {
            floors.forEach { floor ->
                val selected = floor.mapId == currentId
                val background by animateColorAsState(
                    if (selected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent,
                    label = "floor"
                )
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .heightIn(min = 48.dp)
                        .widthIn(min = 48.dp, max = 64.dp)
                        .clip(CircleShape)
                        .background(background)
                        .semantics { contentDescription = floor.name }
                        .clickable(enabled = !selected) { onSelect(floor.mapId) }
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        floorLabel(floor.level),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                        color = if (selected) {
                            MaterialTheme.colorScheme.onPrimaryContainer
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun floorLabel(level: FloorLevel): String = when (level) {
    is FloorLevel.Storey -> if (level.number == 0) {
        stringResource(R.string.map_floor_ground)
    } else {
        stringResource(R.string.map_floor_storey, level.number)
    }

    is FloorLevel.Basement -> stringResource(R.string.map_floor_basement, level.number)

    FloorLevel.Roof -> stringResource(R.string.map_floor_roof)

    FloorLevel.Elevator -> stringResource(R.string.map_floor_elevator)
}

private val FLOORS_MAX_HEIGHT = 360.dp
