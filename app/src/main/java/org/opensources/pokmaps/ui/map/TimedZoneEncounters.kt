package org.opensources.pokmaps.ui.map

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.EncounterFilter
import org.opensources.pokmaps.domain.model.EncounterPeriods
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.byTime
import org.opensources.pokmaps.ui.common.EncounterGroups

@Composable
internal fun TimedZoneEncounters(
    zone: MapZone,
    caught: Set<Int>,
    initialTime: TimeFilter,
    onOpenPokemon: (Int) -> Unit
) {
    var mask by rememberSaveable(zone.mapId) { mutableIntStateOf(initialTime.times.sumOf { 1 shl it.ordinal }) }
    var method by rememberSaveable(zone.mapId) { mutableStateOf(EncounterFilter.ALL) }
    val times = EncounterTime.entries.filter { mask and (1 shl it.ordinal) != 0 }.toSet()
    val periods =
        remember(zone.allEncounters, times) { EncounterPeriods(zone.allEncounters.byTime(TimeFilter.ALL), times) }
    val methods = periods.availableMethods
    val selected = method.takeIf { it in methods } ?: EncounterFilter.ALL
    val sections = remember(zone.allEncounters, times, selected) {
        EncounterPeriods(zone.allEncounters.filter { selected.matches(it) }.byTime(TimeFilter.ALL), times)
    }
    if (periods.available.isNotEmpty()) {
        EncounterPeriodButtons(periods) { period ->
            val next = periods.copy(selected = periods.toggle(period))
            mask = next.selected.sumOf { 1 shl it.ordinal }
            if (method !in next.availableMethods) method = EncounterFilter.ALL
        }
    }
    if (methods.isNotEmpty()) EncounterFilterRow(methods, selected) { method = it }
    if (sections.shown.isEmpty()) {
        Text(stringResource(R.string.map_no_encounter))
    }
    EncounterGroups(
        sections.groups,
        title = { it.pokemonName },
        spritePlace = SpritePlace.MAP_LIST,
        caught = { it.pokemonId in caught },
        onClick = { onOpenPokemon(it.pokemonId) }
    )
}
