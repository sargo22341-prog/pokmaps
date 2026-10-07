package org.opensources.pokmaps.ui.map

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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.CaughtProgress
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SpriteSize

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
                        CaughtProgress(
                            caught = wild.count { it in caught },
                            total = wild.size,
                            modifier = Modifier.padding(start = 8.dp)
                        )
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
    onDismiss: () -> Unit,
    onOpenPlace: (MapPlace) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onShowObject: (Int) -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, bottom = 32.dp)
        ) {
            Text(zone.name, style = MaterialTheme.typography.titleLarge)
            ZoneEncounters(zone, caught, onOpenPokemon)
            ZoneItems(zone, onOpenItem, onShowObject)
            ZonePlaces(zone, onOpenPlace)
        }
    }
}

@Composable
private fun ZoneEncounters(zone: MapZone, caught: Set<Int>, onOpenPokemon: (Int) -> Unit) {
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
            spritePlace = SpritePlace.MAP_LIST,
            spriteSize = SpriteSize.LIST,
            caught = { it.pokemonId in caught },
            onClick = { onOpenPokemon(it.pokemonId) }
        )
    }
}

@Composable
private fun ZoneItems(zone: MapZone, onOpenItem: (String) -> Unit, onShowObject: (Int) -> Unit) {
    if (zone.items.isEmpty()) return
    Text(
        stringResource(R.string.label_items),
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.onSurface,
        modifier = Modifier.padding(top = 16.dp, bottom = 4.dp)
    )
    zone.items.forEach { obj -> ZoneItemRow(obj, onOpenItem, onShowObject) }
}

@Composable
private fun ZoneItemRow(obj: MapObject, onOpenItem: (String) -> Unit, onShowObject: (Int) -> Unit) {
    val identifier = obj.itemIdentifier
    SheetRow(
        title = obj.itemName.orEmpty(),
        subtitle = stringResource(
            if (obj.kind == MapObjectKind.HIDDEN_ITEM) R.string.map_hidden_item else R.string.map_item
        ),
        onClick = identifier?.let { { onOpenItem(it) } },
        onShowOnMap = { onShowObject(obj.id) },
        content = {
            if (identifier != null) PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 48.dp, null)
        }
    )
}

@Composable
private fun ZonePlaces(zone: MapZone, onOpenPlace: (MapPlace) -> Unit) {
    if (zone.places.isEmpty()) return
    Text(
        stringResource(R.string.map_places),
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.onSurface,
        modifier = Modifier.padding(top = 16.dp, bottom = 4.dp)
    )
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        zone.places.forEach { place ->
            FilledTonalButton(onClick = { onOpenPlace(place) }) { Text(place.name) }
        }
    }
}
