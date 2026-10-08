package org.opensources.pokmaps.ui.map

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            modifier = Modifier.widthIn(min = 240.dp)
        ) {
            Text(
                stringResource(R.string.map_choose_world),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )
            state.worlds.forEach { world ->
                DropdownMenuItem(
                    text = { Text(world.name, style = MaterialTheme.typography.titleMedium) },
                    leadingIcon = { Icon(painterResource(R.drawable.ic_map), contentDescription = null) },
                    trailingIcon = {
                        if (world.mapId == state.worldId) {
                            Icon(painterResource(R.drawable.ic_check), stringResource(R.string.map_selected_world))
                        }
                    },
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
internal fun TimeButton(time: TimeFilter, iconOnly: Boolean = false, onClick: () -> Unit) {
    if (iconOnly) {
        FilledTonalIconButton(onClick = onClick) { TimeIcon(time) }
    } else {
        FilledTonalButton(onClick = onClick) {
            TimeIcon(time)
            Text(stringResource(time.label), Modifier.padding(start = 8.dp))
        }
    }
}

@Composable
internal fun TimeIcon(time: TimeFilter) {
    AnimatedContent(
        targetState = time,
        transitionSpec = { fadeIn(tween(1400)) togetherWith fadeOut(tween(1400)) },
        label = "timeIcon"
    ) { period ->
        val icon = when (period) {
            TimeFilter.MORNING -> R.drawable.ic_morning
            TimeFilter.DAY -> R.drawable.ic_day
            TimeFilter.NIGHT -> R.drawable.ic_night
            TimeFilter.ALL -> R.drawable.ic_time_all
        }
        Icon(painterResource(icon), stringResource(period.label), Modifier.size(24.dp))
    }
}

internal val TimeFilter.label: Int
    get() = when (this) {
        TimeFilter.MORNING -> R.string.time_morning
        TimeFilter.DAY -> R.string.time_day
        TimeFilter.NIGHT -> R.string.time_night
        TimeFilter.ALL -> R.string.time_all
    }
