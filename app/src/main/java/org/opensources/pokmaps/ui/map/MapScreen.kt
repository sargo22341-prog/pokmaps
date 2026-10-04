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
import androidx.compose.foundation.layout.heightIn
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
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import ovh.plrapps.mapcompose.ui.MapUI

@Composable
fun MapScreen(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MapViewModel = hiltViewModel()
) {
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
    val versionGroup = state.map?.versionGroupIdentifier.orEmpty()

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
            val detail = state.detail
            val zone = state.zone
            when {
                detail != null -> DetailCard(
                    detail = detail,
                    versionGroupIdentifier = versionGroup,
                    onClose = viewModel::dismissDetail,
                    onOpenPokemon = onOpenPokemon,
                    onOpenItem = onOpenItem
                )

                zone != null -> ZoneBar(
                    zone = zone,
                    closable = state.map?.identifier == GameMap.WORLD,
                    onOpenList = viewModel::openZoneList,
                    onClose = viewModel::clearZone
                )
            }
            SnackbarHost(snackbar)
        }
    }

    val zone = state.zone
    if (state.zoneListOpen && zone != null) {
        ZoneListSheet(
            zone = zone,
            onDismiss = viewModel::closeZoneList,
            onOpenPlace = viewModel::openPlace,
            onOpenPokemon = { id ->
                viewModel.closeZoneList()
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

/** Lieu sélectionné : nom, nombre de Pokémon sauvages et bouton de la liste détaillée. */
@Composable
private fun ZoneBar(zone: MapZone, closable: Boolean, onOpenList: () -> Unit, onClose: () -> Unit) {
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
                Text(
                    when {
                        zone.loading -> ""
                        zone.wildCount == 0 -> stringResource(R.string.map_zone_none)
                        else -> stringResource(R.string.map_zone_summary, zone.wildCount)
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
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
private fun ZoneListSheet(
    zone: MapZone,
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

                zone.encounters.isEmpty() -> Text(
                    stringResource(R.string.map_no_encounter),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 8.dp)
                )

                else -> EncounterGroups(
                    zone.groups,
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
    }
}

/** Fiche de l'élément touché sur la carte, en bas d'écran (la carte reste utilisable). */
@Composable
private fun DetailCard(
    detail: MapDetail,
    versionGroupIdentifier: String,
    onClose: () -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    Surface(
        shape = MaterialTheme.shapes.large,
        tonalElevation = 3.dp,
        shadowElevation = 4.dp,
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Box {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .heightIn(max = DETAIL_MAX_HEIGHT)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
            ) {
                when (detail) {
                    is MapDetail.WildPokemon -> WildPokemonDetails(detail, onOpenPokemon)

                    is MapDetail.Item -> ItemDetailsContent(detail, versionGroupIdentifier, onOpenItem)

                    is MapDetail.Character -> CharacterDetails(
                        detail,
                        versionGroupIdentifier,
                        onOpenPokemon,
                        onOpenItem
                    )
                }
            }
            IconButton(onClick = onClose, modifier = Modifier.align(Alignment.TopEnd)) {
                Icon(painterResource(R.drawable.ic_close), stringResource(R.string.map_close))
            }
        }
    }
}

/** En-tête d'une fiche : image, petite ligne de catégorie et nom. */
@Composable
private fun DetailHeader(label: String, title: String, image: @Composable () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.padding(end = 40.dp)
    ) {
        image()
        Column {
            if (label.isNotEmpty()) {
                Text(
                    label,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(title, style = MaterialTheme.typography.titleLarge)
        }
    }
}

@Composable
private fun WildPokemonDetails(detail: MapDetail.WildPokemon, onOpenPokemon: (Int) -> Unit) {
    DetailHeader(stringResource(R.string.map_wild_pokemon), detail.name) {
        PixelArtImage(Sprites.pokemonIcon(detail.pokemonId), PixelArt.POKEMON_ICON, 64.dp, null)
    }
    EncounterGroups(detail.encounters, title = { it.areaName })
    Button(onClick = { onOpenPokemon(detail.pokemonId) }) {
        Text(stringResource(R.string.map_open_pokemon, detail.name))
    }
}

@Composable
private fun ItemDetailsContent(detail: MapDetail.Item, versionGroupIdentifier: String, onOpenItem: (String) -> Unit) {
    val obj = detail.obj
    val hidden = obj.kind == MapObjectKind.HIDDEN_ITEM
    DetailHeader(
        stringResource(if (hidden) R.string.map_hidden_item else R.string.map_item),
        obj.itemName.orEmpty()
    ) {
        val identifier = obj.itemIdentifier
        val sprite = obj.sprite
        when {
            identifier != null -> PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 48.dp, null)

            sprite != null -> PixelArtImage(
                Sprites.mapSprite(versionGroupIdentifier, sprite),
                PixelArt.MAP_SPRITE,
                48.dp,
                null
            )
        }
    }
    if (hidden) {
        Text(
            stringResource(R.string.map_hidden_item_hint),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
    val details = detail.details ?: return
    details.move?.let { move ->
        Text(stringResource(R.string.map_machine_move, move.name), style = MaterialTheme.typography.titleSmall)
        MoveLine(move)
    }
    details.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
    Button(onClick = { onOpenItem(details.identifier) }) {
        Text(stringResource(R.string.map_open_item, details.name))
    }
}

@Composable
private fun CharacterDetails(
    detail: MapDetail.Character,
    versionGroupIdentifier: String,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    val obj = detail.obj
    val pokemonId = obj.pokemonId
    when (obj.kind) {
        MapObjectKind.POKEMON -> DetailHeader(
            stringResource(R.string.map_static_pokemon, obj.level ?: 0),
            obj.pokemonName.orEmpty()
        ) {
            if (pokemonId != null) PixelArtImage(Sprites.pokemonIcon(pokemonId), PixelArt.POKEMON_ICON, 64.dp, null)
        }

        MapObjectKind.TRAINER -> DetailHeader(
            stringResource(R.string.map_trainer),
            obj.trainerClass?.let(::trainerClassName).orEmpty()
        ) { CharacterSprite(obj, versionGroupIdentifier) }

        else -> DetailHeader("", npcName(obj.sprite)) { CharacterSprite(obj, versionGroupIdentifier) }
    }
    if (pokemonId != null) {
        Button(onClick = { onOpenPokemon(pokemonId) }) {
            Text(stringResource(R.string.map_open_pokemon, obj.pokemonName.orEmpty()))
        }
    }
    if (detail.loading) {
        CircularProgressIndicator(Modifier.size(24.dp))
        return
    }
    if (obj.kind == MapObjectKind.TRAINER) {
        if (detail.party.isEmpty()) {
            Text(stringResource(R.string.map_trainer_starter), style = MaterialTheme.typography.bodyMedium)
        } else {
            SectionTitle(stringResource(R.string.map_trainer_party))
            detail.party.forEach { TrainerPokemonRow(it, onOpenPokemon) }
        }
    }
    // Un personnage qui n'a rien à donner, vendre ni échanger : rien de plus à afficher.
    Offers(detail.offers, onOpenPokemon = onOpenPokemon, onOpenItem = onOpenItem)
}

private val DETAIL_MAX_HEIGHT = 360.dp

private val MapLayer.label: Int
    get() = when (this) {
        MapLayer.WARPS -> R.string.map_layer_warps
        MapLayer.ITEMS -> R.string.map_layer_items
        MapLayer.TRAINERS -> R.string.map_layer_trainers
        MapLayer.POKEMON -> R.string.map_layer_pokemon
    }
