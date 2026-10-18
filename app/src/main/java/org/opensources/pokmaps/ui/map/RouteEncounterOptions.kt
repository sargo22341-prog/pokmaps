package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.Composable
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.ui.common.RouteEncounterOptions

@Composable
internal fun RouteEncounters(
    zone: MapZone,
    caught: Set<Int>,
    timed: Boolean,
    initialTime: TimeFilter,
    onOpenPokemon: (Int) -> Unit
) {
    RouteEncounterOptions(zone.mapId, zone.allEncounters) { encounters ->
        val filtered = zone.copy(encounters = encounters, allEncounters = encounters)
        if (timed && !zone.loading && !zone.failed) {
            TimedZoneEncounters(filtered, caught, initialTime, onOpenPokemon)
        } else {
            FilteredZoneEncounters(filtered, caught, onOpenPokemon)
        }
    }
}
