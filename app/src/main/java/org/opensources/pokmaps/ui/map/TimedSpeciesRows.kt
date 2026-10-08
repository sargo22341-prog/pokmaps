package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.TimedEncounters
import org.opensources.pokmaps.domain.model.TimedSpecies
import org.opensources.pokmaps.ui.common.CaughtIcon
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize
import org.opensources.pokmaps.ui.common.formatNumber

@Composable
internal fun TimedSpeciesRows(section: TimedEncounters, caught: Set<Int>, onOpen: (Int) -> Unit) {
    section.methods.forEach { method ->
        Text(method.name, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        method.species.forEach { species ->
            TimedSpeciesRow(species, species.pokemonId in caught, section.period) { onOpen(species.pokemonId) }
        }
    }
}

@Composable
private fun TimedSpeciesRow(species: TimedSpecies, caught: Boolean, period: TimeFilter, onOpen: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onOpen).padding(vertical = 4.dp)) {
        PokemonSprite(species.pokemonId, SpritePlace.MAP_LIST, SpriteSize.LIST, contentDescription = null)
        Column(Modifier.weight(1f)) {
            Row {
                Text(species.name, style = MaterialTheme.typography.bodyLarge)
                if (caught) CaughtIcon(28.dp)
            }
            species.encounters.forEach { encounter ->
                Text(encounterCaption(encounter, period), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun encounterCaption(encounter: Encounter, period: TimeFilter): String {
    val times = if (period == TimeFilter.ALL && encounter.times.size in 1..2) {
        TimeFilter.entries.filter { it.time in encounter.times }.map { stringResource(it.label) }.joinToString(" / ")
    } else {
        null
    }
    val level = when {
        encounter.isTrade -> null
        encounter.minLevel == encounter.maxLevel -> stringResource(R.string.encounter_levels, encounter.minLevel)
        else -> stringResource(R.string.encounter_level_range, encounter.minLevel, encounter.maxLevel)
    }
    return listOfNotNull(
        times,
        level,
        encounter.chance?.let { stringResource(R.string.encounter_chance, formatNumber(it)) },
        encounter.quantity.takeIf { it > 1 }?.let { stringResource(R.string.encounter_quantity, it) },
        encounter.conditions,
        encounter.note
    ).joinToString(" · ")
}
