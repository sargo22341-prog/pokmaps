package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterGroup

/** Rencontres regroupées par méthode : titre de la méthode puis une ligne par rencontre. */
@Composable
fun EncounterGroups(
    groups: List<EncounterGroup>,
    title: (Encounter) -> String,
    modifier: Modifier = Modifier,
    iconPath: ((Encounter) -> String)? = null,
    onClick: ((Encounter) -> Unit)? = null
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        groups.forEach { group ->
            Text(
                group.methodName,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(top = 8.dp)
            )
            group.encounters.forEach { encounter ->
                EncounterLine(encounter, title(encounter), iconPath?.invoke(encounter), onClick)
            }
        }
    }
}

@Composable
private fun EncounterLine(encounter: Encounter, title: String, iconPath: String?, onClick: ((Encounter) -> Unit)?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick(encounter) } else Modifier)
            .padding(vertical = 2.dp)
    ) {
        if (iconPath != null) AssetImage(iconPath, contentDescription = null, modifier = Modifier.size(40.dp))
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            val details = encounterDetails(encounter)
            if (details.isNotEmpty()) {
                Text(
                    details,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        encounter.chance?.let {
            Text(
                stringResource(R.string.encounter_chance, formatNumber(it)),
                style = MaterialTheme.typography.titleSmall
            )
        }
    }
}

@Composable
private fun encounterDetails(encounter: Encounter): String = listOfNotNull(
    when {
        encounter.isTrade -> null
        encounter.minLevel == encounter.maxLevel -> stringResource(R.string.encounter_levels, encounter.minLevel)
        else -> stringResource(R.string.encounter_level_range, encounter.minLevel, encounter.maxLevel)
    },
    encounter.quantity.takeIf { it > 1 }?.let { stringResource(R.string.encounter_quantity, it) },
    encounter.conditions,
    encounter.note
).joinToString(" · ")
