package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.Image
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
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
    caption: @Composable (Encounter) -> String
) {
    species.forEach { pokemon ->
        val first = pokemon.encounters.first()
        Column(
            Modifier.fillMaxWidth()
                .then(if (onClick == null) Modifier else Modifier.clickable { onClick(first) })
                .padding(vertical = 4.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                spritePlace?.let { PokemonSprite(pokemon.pokemonId, it, spriteSize, contentDescription = null) }
                Text(title(first), style = MaterialTheme.typography.bodyLarge)
                if (caught(first)) CaughtIcon(28.dp)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                WaterMethod.entries.forEach { method ->
                    Column(Modifier.weight(1f)) {
                        WaterMethodDetails(method, pokemon.waterMethods.getValue(method), caption)
                    }
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
        Image(
            painterResource(method.image),
            contentDescription = if (available) label else "$label : ${stringResource(R.string.water_unavailable)}",
            modifier = Modifier.size(28.dp).alpha(if (available) 1f else 0.3f),
            colorFilter = if (available) null else ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) })
        )
        if (encounters.size == 1) WaterChance(encounters.single())
    }
    encounters.forEach { encounter ->
        if (encounters.size > 1) WaterChance(encounter)
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
