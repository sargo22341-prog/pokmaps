package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.EncounterFilter
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.byTime

@Composable
internal fun TimedZoneEncounters(
    zone: MapZone,
    caught: Set<Int>,
    initialTime: TimeFilter,
    onOpenPokemon: (Int) -> Unit
) {
    var filter by rememberSaveable(zone.mapId) { mutableStateOf(initialTime) }
    var method by rememberSaveable(zone.mapId) { mutableStateOf(EncounterFilter.ALL) }
    val sections = remember(zone.allEncounters, filter, method) {
        zone.allEncounters.filter { method.matches(it) }.byTime(filter)
    }
    TimeButton(filter) { filter = filter.next() }
    EncounterFilterRow(method) { method = it }
    if (sections.isEmpty() || sections.all { it.groups.isEmpty() }) {
        Text(stringResource(R.string.map_no_encounter))
    }
    sections.forEach { section ->
        Row(verticalAlignment = Alignment.CenterVertically) {
            TimeIcon(section.period)
            Text(
                stringResource(if (section.period == TimeFilter.ALL) R.string.time_always else section.period.label),
                style = MaterialTheme.typography.titleMedium
            )
        }
        TimedSpeciesRows(section, caught, onOpenPokemon)
    }
}
