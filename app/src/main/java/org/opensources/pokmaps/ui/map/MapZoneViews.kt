package org.opensources.pokmaps.ui.map

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.CaughtIcon
import org.opensources.pokmaps.ui.common.CompleteIcon
import org.opensources.pokmaps.ui.common.EncounterGroups

// Lieu sélectionné sur la carte : barre du bas et liste détaillée.

/** Lieu sélectionné : nom, nombre de Pokémon sauvages et bouton de la liste détaillée. */
@Composable
internal fun ZoneBar(zone: MapZone, caught: Set<Int>, closable: Boolean, onOpenList: () -> Unit, onClose: () -> Unit) {
    Surface(
        shape = MaterialTheme.shapes.large,
        tonalElevation = 3.dp,
        shadowElevation = 4.dp,
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(start = 16.dp, top = 4.dp, bottom = 4.dp, end = 4.dp)
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    zone.name,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                val wild = zone.wildIds
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        when {
                            zone.loading -> ""
                            wild.isEmpty() -> stringResource(R.string.map_zone_none)
                            else -> pluralStringResource(R.plurals.map_zone_summary, wild.size, wild.size)
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (!zone.loading && wild.isNotEmpty()) {
                        CaughtProgress(caught = wild.count { it in caught }, total = wild.size)
                    }
                }
            }
            FilledTonalButton(onClick = onOpenList) {
                Icon(
                    painterResource(R.drawable.ic_list),
                    contentDescription = stringResource(R.string.map_zone_list_description),
                    modifier = Modifier
                        .padding(end = 6.dp)
                        .size(18.dp)
                )
                Text(stringResource(R.string.map_zone_list))
            }
            if (closable) {
                IconButton(onClick = onClose) {
                    Icon(painterResource(R.drawable.ic_close), stringResource(R.string.map_close))
                }
            }
        }
    }
}

/** Liste détaillée du lieu : Pokémon par méthode (niveaux, probabilités) et lieux accessibles. */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
internal fun ZoneListSheet(
    zone: MapZone,
    caught: Set<Int>,
    animated: Boolean,
    onDismiss: () -> Unit,
    onOpenPlace: (MapPlace) -> Unit,
    onOpenPokemon: (Int) -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, bottom = 32.dp)
        ) {
            Text(zone.name, style = MaterialTheme.typography.titleLarge)
            when {
                zone.loading -> CircularProgressIndicator(Modifier.padding(16.dp))

                zone.failed -> Text(
                    stringResource(R.string.data_load_error),
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(vertical = 8.dp)
                )

                zone.encounters.isEmpty() -> Text(
                    stringResource(R.string.map_no_encounter),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 8.dp)
                )

                else -> EncounterGroups(
                    zone.groups,
                    title = { it.pokemonName },
                    iconPath = { Sprites.pokemonIcon(it.pokemonId) },
                    iconWidth = LIST_ICON_WIDTH,
                    animatedIcons = animated,
                    caught = { it.pokemonId in caught },
                    onClick = { onOpenPokemon(it.pokemonId) }
                )
            }
            if (zone.places.isNotEmpty()) {
                Text(
                    stringResource(R.string.map_places),
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(top = 16.dp, bottom = 4.dp)
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    zone.places.forEach { place ->
                        FilledTonalButton(onClick = { onOpenPlace(place) }) { Text(place.name) }
                    }
                }
            }
        }
    }
}

/**
 * Pokémon sauvages capturés : Poké Ball et « 1/2 », ou Master Ball et coche quand le lieu est terminé
 * (tous capturés), avec une petite animation au moment où il le devient.
 */
@Composable
private fun CaughtProgress(caught: Int, total: Int) {
    AnimatedContent(
        targetState = caught >= total,
        transitionSpec = { (scaleIn() + fadeIn()) togetherWith fadeOut() },
        label = "progress"
    ) { complete ->
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 8.dp)) {
            if (complete) {
                CompleteIcon(PROGRESS_ICON)
                Icon(
                    painterResource(R.drawable.ic_check),
                    contentDescription = stringResource(R.string.map_zone_complete),
                    tint = COMPLETE_COLOR,
                    modifier = Modifier.size(16.dp)
                )
            } else {
                CaughtIcon(PROGRESS_ICON)
                Text(
                    stringResource(R.string.map_zone_caught, caught, total),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

private val LIST_ICON_WIDTH = 112.dp
private val PROGRESS_ICON = 24.dp
private val COMPLETE_COLOR = Color(0xFF43A047)
