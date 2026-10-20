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
import org.opensources.pokmaps.domain.model.SpritePlace

/**
 * Rencontres regroupées par méthode : titre de la méthode puis une ligne par rencontre, avec le sprite du Pokémon
 * si `spritePlace` est donné (animé selon le réglage de cet endroit).
 */
@Composable
fun EncounterGroups(
    groups: List<EncounterGroup>,
    title: (Encounter) -> String,
    modifier: Modifier = Modifier,
    spritePlace: SpritePlace? = null,
    spriteSize: SpriteSize = SpriteSize.LIST,
    caught: (Encounter) -> Boolean = { false },
    onClick: ((Encounter) -> Unit)? = null
) {
    Column(modifier) {
        groups.forEach { group ->
            if (group.aquatic) {
                WaterEncounterRows(group.species, title, spritePlace, spriteSize, caught, onClick) {
                    encounterDetails(it)
                }
            } else if (group.water) {
                EncounterWaterZone(group.habitat) {
                    EncounterWaterCard(group.habitat) {
                        Column(Modifier.padding(12.dp)) {
                            EncounterMethodRows(group, title, spritePlace, spriteSize, caught, onClick)
                        }
                    }
                }
            } else {
                EncounterLandSection(group.habitat, enabled = group.landscape) {
                    EncounterMethodRows(group, title, spritePlace, spriteSize, caught, onClick)
                }
            }
        }
    }
}

@Composable
private fun EncounterMethodRows(
    group: EncounterGroup,
    title: (Encounter) -> String,
    spritePlace: SpritePlace?,
    spriteSize: SpriteSize,
    caught: (Encounter) -> Boolean,
    onClick: ((Encounter) -> Unit)?
) {
    when {
        group.headbutt -> Text(
            stringResource(R.string.encounter_headbutt_title),
            style = MaterialTheme.typography.titleSmall
        )

        group.honeyTrees -> Text(
            stringResource(R.string.method_honey_tree),
            style = MaterialTheme.typography.titleSmall
        )

        else -> Text(group.methodName, style = MaterialTheme.typography.titleSmall)
    }
    if (group.landscape) {
        group.species.forEach { species ->
            EncounterVariantRow(species, title, spritePlace, spriteSize, caught, onClick)
        }
    } else {
        group.encounters.forEach { encounter ->
            EncounterLine(
                encounter,
                title(encounter),
                spritePlace?.let { EncounterSprite(it, spriteSize) },
                caught(encounter),
                onClick
            )
        }
    }
}

/** Sprite des Pokémon d'une liste de rencontres : endroit (réglage des sprites animés) et taille. */
private data class EncounterSprite(val place: SpritePlace, val size: SpriteSize)

@Composable
private fun EncounterLine(
    encounter: Encounter,
    title: String,
    sprite: EncounterSprite?,
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
        // Cadre de taille fixe : les lignes restent alignées, quel que soit le Pokémon.
        sprite?.let { PokemonSprite(encounter.pokemonId, it.place, it.size, contentDescription = null) }
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.bodyLarge)
                if (caught) CaughtIcon(28.dp)
            }
            if (encounter.needsExternalEventLabel) ExternalEventLabel()
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
internal fun encounterDetails(encounter: Encounter): String = listOfNotNull(
    encounterLevel(encounter),
    encounterContext(encounter).takeIf { it.isNotEmpty() }
).joinToString(" · ")

@Composable
internal fun encounterLevel(encounter: Encounter): String? = when {
    encounter.isTrade -> null
    encounter.minLevel == encounter.maxLevel -> stringResource(R.string.encounter_levels, encounter.minLevel)
    else -> stringResource(R.string.encounter_level_range, encounter.minLevel, encounter.maxLevel)
}

@Composable
internal fun encounterContext(encounter: Encounter): String = listOfNotNull(
    encounter.quantity.takeIf { it > 1 }?.let { stringResource(R.string.encounter_quantity, it) },
    encounter.conditions,
    encounter.note
).joinToString(" · ")
