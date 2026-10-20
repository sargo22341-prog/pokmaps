package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterHabitat
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.TimedSpecies
import org.opensources.pokmaps.domain.model.WaterMethod

@Composable
internal fun WaterEncounterRows(
    species: List<TimedSpecies>,
    title: (Encounter) -> String,
    spritePlace: SpritePlace?,
    spriteSize: SpriteSize,
    caught: (Encounter) -> Boolean,
    onClick: ((Encounter) -> Unit)?,
    inWaterZone: Boolean = false,
    caption: @Composable (Encounter) -> String
) {
    val habitat = species.firstOrNull()?.encounters?.firstOrNull()?.habitat ?: EncounterHabitat.GRASS
    if (inWaterZone) {
        WaterSpeciesCards(species, title, spritePlace, spriteSize, caught, onClick, caption)
    } else {
        EncounterWaterZone(habitat) {
            WaterSpeciesCards(species, title, spritePlace, spriteSize, caught, onClick, caption)
        }
    }
}

@Composable
private fun WaterSpeciesCards(
    species: List<TimedSpecies>,
    title: (Encounter) -> String,
    spritePlace: SpritePlace?,
    spriteSize: SpriteSize,
    caught: (Encounter) -> Boolean,
    onClick: ((Encounter) -> Unit)?,
    caption: @Composable (Encounter) -> String
) {
    species.forEach { pokemon ->
        val first = pokemon.encounters.first()
        EncounterWaterCard(first.habitat, Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(
                Modifier.fillMaxWidth()
                    .then(if (onClick == null) Modifier else Modifier.clickable { onClick(first) })
                    .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    WaterMethod.entries.forEach { method ->
                        Column(Modifier.weight(1f)) {
                            WaterMethodDetails(method, pokemon.waterMethods.getValue(method), caption)
                        }
                    }
                }
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    spritePlace?.let { PokemonSprite(pokemon.pokemonId, it, spriteSize, contentDescription = null) }
                    Text(title(first), style = MaterialTheme.typography.bodyLarge)
                    if (caught(first)) CaughtIcon(28.dp)
                }
            }
        }
    }
}

@Composable
private fun WaterMethodDetails(
    method: WaterMethod,
    encounters: List<Encounter>,
    caption: @Composable (Encounter) -> String
) {
    val available = encounters.isNotEmpty()
    val label = stringResource(method.label)
    Row(verticalAlignment = Alignment.CenterVertically) {
        EncounterAvailabilityIcon(method.image, label, available)
        if (encounters.size == 1) WaterChance(encounters.single())
    }
    encounters.forEach { encounter ->
        if (encounters.size > 1) WaterChance(encounter)
        EncounterTimeIcons(encounter)
        Text(caption(encounter), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun WaterChance(encounter: Encounter) {
    encounter.chance?.let {
        Text(stringResource(R.string.encounter_chance, formatNumber(it)), style = MaterialTheme.typography.labelSmall)
    }
}

private val WaterMethod.image: Int
    get() = when (this) {
        WaterMethod.SURF -> R.drawable.encounter_surf
        WaterMethod.OLD_ROD -> R.drawable.encounter_old_rod
        WaterMethod.GOOD_ROD -> R.drawable.encounter_good_rod
        WaterMethod.SUPER_ROD -> R.drawable.encounter_super_rod
    }

private val WaterMethod.label: Int
    get() = when (this) {
        WaterMethod.SURF -> R.string.method_surf
        WaterMethod.OLD_ROD -> R.string.water_old_rod
        WaterMethod.GOOD_ROD -> R.string.water_good_rod
        WaterMethod.SUPER_ROD -> R.string.water_super_rod
    }
