package org.opensources.pokmaps.ui.map

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.EncounterGroups
import ovh.plrapps.mapcompose.ui.MapUI

@Composable
fun MapScreen(onOpenPokemon: (Int) -> Unit, modifier: Modifier = Modifier, viewModel: MapViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val notFoundMessage = state.notFound?.let {
        stringResource(R.string.map_highlight_none, it, state.game?.name.orEmpty())
    }
    LaunchedEffect(notFoundMessage) {
        if (notFoundMessage != null) {
            viewModel.notFoundShown()
            snackbar.showSnackbar(notFoundMessage)
        }
    }
    BackHandler(enabled = state.previous != null, onBack = viewModel::back)

    Box(modifier.fillMaxSize()) {
        val mapState = state.mapState
        if (mapState == null) {
            CircularProgressIndicator(Modifier.align(Alignment.Center))
        } else {
            MapUI(Modifier.fillMaxSize(), state = mapState)
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .align(Alignment.TopStart)
                .fillMaxWidth()
                .padding(8.dp)
        ) {
            MapTitle(state, viewModel::back, Modifier.weight(1f))
            LayersButton(state.layers, viewModel::toggleLayer)
        }
        Column(Modifier.align(Alignment.BottomCenter)) {
            state.highlight?.let { highlight ->
                HighlightBanner(highlight, onOpen = viewModel::openPlace, onClose = viewModel::clearHighlight)
            }
            SnackbarHost(snackbar)
        }
    }

    state.selection?.let { selection ->
        SelectionSheet(
            selection = selection,
            versionGroupIdentifier = state.map?.versionGroupIdentifier.orEmpty(),
            onDismiss = viewModel::dismissSelection,
            onOpenPlace = viewModel::openPlace,
            onOpenPokemon = { id ->
                viewModel.dismissSelection()
                onOpenPokemon(id)
            }
        )
    }
}

/** Nom de la carte affichée, avec le retour à la carte précédente. */
@Composable
private fun MapTitle(state: MapUiState, onBack: () -> Unit, modifier: Modifier = Modifier) {
    val map = state.map ?: return
    Row(modifier) {
        Surface(shape = MaterialTheme.shapes.medium, tonalElevation = 3.dp, shadowElevation = 2.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(end = 12.dp)) {
                val previous = state.previous
                if (previous != null) {
                    IconButton(onClick = onBack) {
                        Icon(painterResource(R.drawable.ic_back), stringResource(R.string.map_back_to, previous.name))
                    }
                } else {
                    Box(Modifier.size(12.dp))
                }
                Text(
                    map.name,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(vertical = 10.dp)
                )
            }
        }
    }
}

@Composable
private fun LayersButton(layers: Set<MapLayer>, onToggle: (MapLayer) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        FilledTonalIconButton(onClick = { expanded = true }) {
            Icon(painterResource(R.drawable.ic_layers), stringResource(R.string.map_layers))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            MapLayer.entries.forEach { layer ->
                DropdownMenuItem(
                    text = { Text(stringResource(layer.label)) },
                    leadingIcon = { Checkbox(checked = layer in layers, onCheckedChange = null) },
                    onClick = { onToggle(layer) }
                )
            }
        }
    }
}

@Composable
private fun HighlightBanner(highlight: MapHighlight, onOpen: (MapPlace) -> Unit, onClose: () -> Unit) {
    Surface(
        shape = MaterialTheme.shapes.large,
        tonalElevation = 3.dp,
        shadowElevation = 4.dp,
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Column(Modifier.padding(vertical = 8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 16.dp)) {
                AssetImage(
                    Sprites.pokemonIcon(highlight.pokemonId),
                    contentDescription = null,
                    modifier = Modifier.size(32.dp)
                )
                Text(
                    stringResource(R.string.map_highlight, highlight.name),
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier
                        .weight(1f)
                        .padding(start = 8.dp)
                )
                IconButton(onClick = onClose) {
                    Icon(painterResource(R.drawable.ic_close), stringResource(R.string.map_highlight_clear))
                }
            }
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(horizontal = 16.dp)
            ) {
                items(highlight.places, key = { it.mapId }) { place ->
                    AssistChip(onClick = { onOpen(place) }, label = { Text(place.name) })
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SelectionSheet(
    selection: MapSelection,
    versionGroupIdentifier: String,
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
            when (selection) {
                is MapSelection.Zone -> ZoneDetails(selection, onOpenPlace, onOpenPokemon)
                is MapSelection.Object -> ObjectDetails(selection.obj, versionGroupIdentifier, onOpenPokemon)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ZoneDetails(zone: MapSelection.Zone, onOpenPlace: (MapPlace) -> Unit, onOpenPokemon: (Int) -> Unit) {
    Text(zone.name, style = MaterialTheme.typography.titleLarge)
    when {
        zone.loading -> CircularProgressIndicator(Modifier.padding(16.dp))

        zone.encounters.isEmpty() -> Text(
            stringResource(R.string.map_no_encounter),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(vertical = 8.dp)
        )

        else -> EncounterGroups(
            zone.encounters,
            title = { it.pokemonName },
            iconPath = { Sprites.pokemonIcon(it.pokemonId) },
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

@Composable
private fun ObjectDetails(obj: MapObject, versionGroupIdentifier: String, onOpenPokemon: (Int) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        val sprite = obj.sprite
        val item = obj.itemIdentifier
        when {
            obj.pokemonId != null -> AssetImage(Sprites.pokemonIcon(obj.pokemonId), null, Modifier.size(56.dp))
            item != null -> AssetImage(Sprites.item(item), null, Modifier.size(40.dp))
            sprite != null -> AssetImage(Sprites.mapSprite(versionGroupIdentifier, sprite), null, Modifier.size(40.dp))
        }
        Column {
            Text(
                when (obj.kind) {
                    MapObjectKind.ITEM -> stringResource(R.string.map_item)
                    MapObjectKind.HIDDEN_ITEM -> stringResource(R.string.map_hidden_item)
                    MapObjectKind.TRAINER -> stringResource(R.string.map_trainer)
                    MapObjectKind.POKEMON -> stringResource(R.string.map_static_pokemon, obj.level ?: 0)
                    MapObjectKind.NPC -> ""
                },
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                obj.pokemonName ?: obj.itemName ?: obj.trainerClass?.let(::trainerClassName).orEmpty(),
                style = MaterialTheme.typography.titleLarge
            )
        }
    }
    val pokemonId = obj.pokemonId
    if (pokemonId != null) {
        Button(onClick = { onOpenPokemon(pokemonId) }, modifier = Modifier.padding(top = 16.dp)) {
            Text(stringResource(R.string.map_open_pokemon, obj.pokemonName.orEmpty()))
        }
    }
}

private val MapLayer.label: Int
    get() = when (this) {
        MapLayer.WARPS -> R.string.map_layer_warps
        MapLayer.ITEMS -> R.string.map_layer_items
        MapLayer.TRAINERS -> R.string.map_layer_trainers
        MapLayer.POKEMON -> R.string.map_layer_pokemon
    }
