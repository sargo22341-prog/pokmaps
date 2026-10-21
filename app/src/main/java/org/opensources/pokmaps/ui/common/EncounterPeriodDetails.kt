package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.TimedSpecies

@Composable
internal fun EncounterPeriodDetails(species: TimedSpecies) {
    if (!species.encounters.first().hasTimeOfDay) {
        species.variants.forEach { EncounterVariantCaption(it) }
        return
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        EncounterTime.entries.forEach { time ->
            val encounters = species.periods.getValue(time)
            Column(Modifier.weight(1f)) {
                EncounterPeriodIcon(time, encounters.isNotEmpty())
                encounters.forEach { encounter -> EncounterVariantCaption(encounter) }
            }
        }
    }
}

@Composable
internal fun EncounterTimeIcons(encounter: Encounter) {
    if (!encounter.hasTimeOfDay) return
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        EncounterTime.entries.forEach { time ->
            EncounterPeriodIcon(time, encounter.times.isEmpty() || time in encounter.times, size = 20.dp)
        }
    }
}

@Composable
private fun EncounterPeriodIcon(time: EncounterTime, available: Boolean, size: Dp = 28.dp) {
    val image = when (time) {
        EncounterTime.MORNING -> R.drawable.ic_morning
        EncounterTime.DAY -> R.drawable.ic_day
        EncounterTime.NIGHT -> R.drawable.ic_night
    }
    val label = when (time) {
        EncounterTime.MORNING -> R.string.time_morning
        EncounterTime.DAY -> R.string.time_day
        EncounterTime.NIGHT -> R.string.time_night
    }
    EncounterAvailabilityIcon(
        image,
        stringResource(R.string.encounter_time_icon, stringResource(label)),
        available,
        size
    )
}

@Composable
internal fun EncounterVariantCaption(encounter: Encounter) {
    val summary = listOfNotNull(
        encounterLevel(encounter),
        encounter.chance?.let { stringResource(R.string.encounter_chance, formatNumber(it)) }
    ).joinToString(" · ")
    Text(summary, style = MaterialTheme.typography.bodySmall)
    val context = encounterContext(encounter)
    if (context.isNotEmpty()) Text(context, style = MaterialTheme.typography.bodySmall)
}
