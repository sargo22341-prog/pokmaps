package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.TimedSpecies

@Composable
internal fun EncounterVariantRow(
    species: TimedSpecies,
    title: (Encounter) -> String,
    spritePlace: SpritePlace?,
    spriteSize: SpriteSize,
    caught: (Encounter) -> Boolean,
    onClick: ((Encounter) -> Unit)?
) {
    val first = species.encounters.first()
    Row(
        Modifier.fillMaxWidth()
            .then(if (onClick == null) Modifier else Modifier.clickable { onClick(first) })
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        spritePlace?.let { PokemonSprite(species.pokemonId, it, spriteSize, contentDescription = null) }
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(title(first), style = MaterialTheme.typography.bodyLarge)
                if (caught(first)) CaughtIcon(28.dp)
            }
            if (first.needsExternalEventLabel) ExternalEventLabel()
            if (species.trees) {
                TreeEncounterDetails(species)
            } else {
                EncounterPeriodDetails(species)
            }
        }
    }
}
