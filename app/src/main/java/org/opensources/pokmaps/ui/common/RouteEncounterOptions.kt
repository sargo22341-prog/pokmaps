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
import org.opensources.pokmaps.domain.model.EncounterRadio
import org.opensources.pokmaps.domain.model.GbaCartridge
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.RouteEncounterFilter

@Composable
internal fun RouteEncounterOptions(
    key: Int,
    encounters: List<Encounter>,
    content: @Composable (List<Encounter>) -> Unit
) {
    var cartridge by rememberSaveable(key) { mutableStateOf(GbaCartridge.NONE) }
    var gifts by rememberSaveable(key) { mutableStateOf(false) }
    var roaming by rememberSaveable(key) { mutableStateOf(false) }
    var radar by rememberSaveable(key) { mutableStateOf(false) }
    var swarm by rememberSaveable(key) { mutableStateOf(false) }
    var national by rememberSaveable(key) { mutableStateOf(false) }
    var daily by rememberSaveable(key) { mutableStateOf(false) }
    var radio by rememberSaveable(key) { mutableStateOf(EncounterRadio.OFF) }
    val filter = RouteEncounterFilter(
        cartridge,
        roaming,
        radar,
        swarm,
        national || daily || cartridge != GbaCartridge.NONE || radio != EncounterRadio.OFF,
        daily,
        gifts,
        radio
    )
    val keys = remember(encounters) { encounters.flatMap { it.conditionKeys }.toSet() }
    if (!roaming && !gifts && keys.any { it.startsWith("radio-") }) RadioSelector(radio) { radio = it }
    if (!roaming && !gifts && keys.any { it.startsWith("slot2-") }) {
        CompactSelect(cartridge, GbaCartridge.entries, { cartridge = it }) { stringResource(it.label) }
    }
    if (!roaming && !gifts && "backlot-mentioned" in keys) {
        FilterChip(daily, { daily = !daily }, { Text(stringResource(R.string.route_daily)) })
    }
    RouteSwitches(
        encounters,
        filter,
        keys,
        {
            roaming = !roaming
            gifts = false
        },
        { radar = !radar },
        { swarm = !swarm },
        { national = !national }
    )
    if (encounters.any { ObtainMethod.fromEncounterMethod(it.method) == ObtainMethod.GIFT }) {
        FilterChip(gifts, {
            gifts = !gifts
            roaming = false
        }, { Text(stringResource(R.string.route_gifts)) })
    }
    val filtered = remember(encounters, filter) { filter.apply(encounters) }
    content(filtered)
}

@Composable
private fun RadioSelector(selected: EncounterRadio, onSelect: (EncounterRadio) -> Unit) {
    CompactSelect(selected, EncounterRadio.entries, onSelect) {
        stringResource(
            when (it) {
                EncounterRadio.OFF -> R.string.route_radio_off
                EncounterRadio.HOENN -> R.string.route_radio_hoenn
                EncounterRadio.SINNOH -> R.string.route_radio_sinnoh
            }
        )
    }
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
        if (!filter.roaming && !filter.gifts && "story-progress-national-dex" in keys &&
            filter.cartridge == GbaCartridge.NONE && !filter.daily && filter.radio == EncounterRadio.OFF
        ) {
            FilterChip(filter.nationalDex, onNational, { Text(stringResource(R.string.route_national)) })
        }
        if (!filter.roaming && !filter.gifts && "radar-on" in keys) {
            FilterChip(filter.radar, onRadar, { Text(stringResource(R.string.route_radar)) })
        }
        if (!filter.roaming && !filter.gifts && "swarm-yes" in keys) {
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
