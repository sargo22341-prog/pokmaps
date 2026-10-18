package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.GbaCartridge
import org.opensources.pokmaps.domain.model.RouteEncounterFilter

@Composable
internal fun RouteEncounterOptions(
    key: Int,
    encounters: List<Encounter>,
    content: @Composable (List<Encounter>) -> Unit
) {
    var cartridge by rememberSaveable(key) { mutableStateOf(GbaCartridge.NONE) }
    var roaming by rememberSaveable(key) { mutableStateOf(false) }
    var radar by rememberSaveable(key) { mutableStateOf(false) }
    var swarm by rememberSaveable(key) { mutableStateOf(false) }
    var national by rememberSaveable(key) { mutableStateOf(false) }
    var daily by rememberSaveable(key) { mutableStateOf(false) }
    val filter = RouteEncounterFilter(
        cartridge,
        roaming,
        radar,
        swarm,
        national || daily || cartridge != GbaCartridge.NONE,
        daily
    )
    val keys = remember(encounters) { encounters.flatMap { it.conditionKeys }.toSet() }
    if (!roaming && keys.any { it.startsWith("slot2-") }) {
        CompactSelect(cartridge, GbaCartridge.entries, { cartridge = it }) { stringResource(it.label) }
    }
    if (!roaming && "backlot-mentioned" in keys) {
        FilterChip(daily, { daily = !daily }, { Text(stringResource(R.string.route_daily)) })
    }
    RouteSwitches(
        encounters,
        filter,
        keys,
        { roaming = !roaming },
        { radar = !radar },
        { swarm = !swarm },
        { national = !national }
    )
    val filtered = remember(encounters, filter) { filter.apply(encounters) }
    content(filtered)
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RouteSwitches(
    encounters: List<Encounter>,
    filter: RouteEncounterFilter,
    keys: Set<String>,
    onRoaming: () -> Unit,
    onRadar: () -> Unit,
    onSwarm: () -> Unit,
    onNational: () -> Unit
) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        if (encounters.any { it.method.startsWith("roaming-") }) {
            FilterChip(filter.roaming, onRoaming, { Text(stringResource(R.string.route_roaming)) })
        }
        if (!filter.roaming && "story-progress-national-dex" in keys &&
            filter.cartridge == GbaCartridge.NONE && !filter.daily
        ) {
            FilterChip(filter.nationalDex, onNational, { Text(stringResource(R.string.route_national)) })
        }
        if (!filter.roaming && "radar-on" in keys) {
            FilterChip(filter.radar, onRadar, { Text(stringResource(R.string.route_radar)) })
        }
        if (!filter.roaming && "swarm-yes" in keys) {
            FilterChip(filter.swarm, onSwarm, { Text(stringResource(R.string.route_swarm)) })
        }
    }
}

private val GbaCartridge.label: Int
    get() = when (this) {
        GbaCartridge.NONE -> R.string.route_gba_none
        GbaCartridge.RUBY -> R.string.route_gba_ruby
        GbaCartridge.SAPPHIRE -> R.string.route_gba_sapphire
        GbaCartridge.EMERALD -> R.string.route_gba_emerald
        GbaCartridge.FIRERED -> R.string.route_gba_firered
        GbaCartridge.LEAFGREEN -> R.string.route_gba_leafgreen
    }
