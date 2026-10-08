package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.EncounterTime

@Composable
internal fun MapFilters(state: MapUiState, onAction: (MapAction) -> Unit, modifier: Modifier = Modifier) {
    Column(modifier) {
        if (state.worlds.size > 1) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.worlds, key = { it.mapId }) { world ->
                    FilterChip(
                        selected = state.worldId == world.mapId,
                        onClick = { onAction(MapAction.SelectWorld(world.mapId)) },
                        label = { Text(world.name) },
                        modifier = Modifier.heightIn(min = 48.dp)
                    )
                }
            }
        }
        if (state.game?.generationId == 2) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(EncounterTime.entries, key = { it.identifier }) { time ->
                    FilterChip(
                        selected = time in state.times,
                        onClick = { onAction(MapAction.ToggleTime(time)) },
                        label = { Text(stringResource(time.label)) },
                        modifier = Modifier.heightIn(min = 48.dp)
                    )
                }
            }
        }
    }
}

private val EncounterTime.label: Int
    get() = when (this) {
        EncounterTime.MORNING -> R.string.time_morning
        EncounterTime.DAY -> R.string.time_day
        EncounterTime.NIGHT -> R.string.time_night
    }
