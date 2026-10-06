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
import androidx.compose.ui.unit.Dp
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
    iconWidth: Dp = 56.dp,
    animatedIcons: Boolean = false,
    caught: (Encounter) -> Boolean = { false },
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
                EncounterLine(
                    encounter,
                    title(encounter),
                    iconPath?.invoke(encounter),
                    iconWidth,
                    animatedIcons,
                    caught(encounter),
                    onClick
                )
            }
        }
    }
}

@Composable
private fun EncounterLine(
    encounter: Encounter,
    title: String,
    iconPath: String?,
    iconWidth: Dp,
    animatedIcon: Boolean,
    caught: Boolean,
    onClick: ((Encounter) -> Unit)?
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick(encounter) } else Modifier)
            .padding(vertical = 2.dp)
    ) {
        when {
            iconPath == null -> Unit

            // Sprite animé dans la place qu'occuperait l'icône : les lignes restent alignées.
            animatedIcon -> {
                val size = pixelArtSize(PixelArt.POKEMON_ICON, iconWidth)
                AnimatedPokemonSprite(
                    encounter.pokemonId,
                    contentDescription = null,
                    modifier = Modifier.size(
                        size.width * PixelArt.POKEMON_CONTENT_WIDTH,
                        size.height * PixelArt.POKEMON_CONTENT_HEIGHT
                    )
                )
            }

            else -> PokemonIconImage(iconPath, iconWidth, contentDescription = null)
        }
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.bodyLarge)
                if (caught) CaughtIcon(28.dp)
            }
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
