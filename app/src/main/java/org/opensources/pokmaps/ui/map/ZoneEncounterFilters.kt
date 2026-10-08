package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.EncounterFilter

@Composable
internal fun FilteredZoneEncounters(zone: MapZone, caught: Set<Int>, onOpenPokemon: (Int) -> Unit) {
    var method by rememberSaveable(zone.mapId) { mutableStateOf(EncounterFilter.ALL) }
    val filtered = remember(zone, method) {
        zone.copy(encounters = zone.allEncounters.filter { method.matches(it) })
    }
    if (!zone.loading && !zone.failed) EncounterFilterRow(method) { method = it }
    ZoneEncounters(filtered, caught, onOpenPokemon)
}

@Composable
internal fun EncounterFilterRow(selected: EncounterFilter, onSelect: (EncounterFilter) -> Unit) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(vertical = 4.dp)) {
        items(EncounterFilter.entries, key = { it.name }) { method ->
            FilterChip(
                selected = selected == method,
                onClick = { onSelect(method) },
                label = { Text(stringResource(method.label)) }
            )
        }
    }
}

private val EncounterFilter.label: Int
    get() = when (this) {
        EncounterFilter.ALL -> R.string.time_all
        EncounterFilter.WALK -> R.string.map_method_walk
        EncounterFilter.FISHING -> R.string.method_fishing
        EncounterFilter.SURF -> R.string.method_surf
    }
