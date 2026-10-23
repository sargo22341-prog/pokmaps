package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.TimedSpecies

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun TreeEncounterDetails(species: TimedSpecies) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        species.variants.forEach { encounter ->
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val image = when (encounter.method) {
                        "headbutt-high" -> R.drawable.encounter_tree_high
                        "honey-tree" -> R.drawable.encounter_tree_honey
                        else -> R.drawable.encounter_tree
                    }
                    EncounterAvailabilityIcon(image, encounter.methodName, available = true)
                    encounter.chance?.let {
                        Text(
                            stringResource(R.string.encounter_chance, formatNumber(it)),
                            style = MaterialTheme.typography.labelSmall
                        )
                    }
                }
                if (encounter.method in setOf("headbutt-common", "headbutt-rare", "headbutt-secret")) {
                    Text(encounter.methodName, style = MaterialTheme.typography.labelSmall)
                }
                if (encounter.times.isNotEmpty()) EncounterTimeIcons(encounter)
                Text(encounterDetails(encounter), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
