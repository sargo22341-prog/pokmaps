package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.TimeFilter

@Composable
internal fun WorldSelector(state: MapUiState, onAction: (MapAction) -> Unit, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        state.parent?.let { parent ->
            IconButton(onClick = { onAction(MapAction.Back) }) {
                Icon(painterResource(R.drawable.ic_back), stringResource(R.string.map_back_to, parent.name))
            }
        }
        WorldMenu(state, onAction)
    }
}

@Composable
private fun WorldMenu(state: MapUiState, onAction: (MapAction) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        FilledTonalButton(onClick = { expanded = true }) {
            Text(state.worlds.firstOrNull { it.mapId == state.worldId }?.name.orEmpty())
            Icon(painterResource(R.drawable.ic_arrow_down), contentDescription = null, modifier = Modifier.size(18.dp))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            state.worlds.forEach { world ->
                DropdownMenuItem(
                    text = { Text(world.name) },
                    onClick = {
                        expanded = false
                        onAction(MapAction.SelectWorld(world.mapId))
                    }
                )
            }
        }
    }
}

@Composable
internal fun TimeButton(time: TimeFilter, onClick: () -> Unit) {
    FilledTonalButton(onClick = onClick) { Text(stringResource(time.label)) }
}

internal val TimeFilter.label: Int
    get() = when (this) {
        TimeFilter.MORNING -> R.string.time_morning
        TimeFilter.DAY -> R.string.time_day
        TimeFilter.NIGHT -> R.string.time_night
        TimeFilter.ALL -> R.string.time_all
    }
