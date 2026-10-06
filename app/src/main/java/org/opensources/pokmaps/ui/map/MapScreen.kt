package org.opensources.pokmaps.ui.map

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.FloorLevel
import org.opensources.pokmaps.domain.map.MapFloor
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AnimatedPokemonSprite
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.CaughtIcon
import org.opensources.pokmaps.ui.common.CompleteIcon
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
    // Retour sur la carte (après le Pokédex, une fiche…) : la carte est recréée pour que les touches remarchent.
    LaunchedEffect(Unit) { viewModel.onScreenShown() }
    MapScreenContent(state, onOpenPokemon, onOpenItem, modifier, viewModel)
}

@Composable
private fun MapScreenContent(
    state: MapUiState,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier,
    viewModel: MapViewModel
) {
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
    // Retour : vers le niveau du dessus (bâtiment, ville ou route), ou désélection du lieu sur la carte du monde.
    val isWorld = state.map?.identifier == GameMap.WORLD
    BackHandler(enabled = state.parent != null || (isWorld && state.zone != null), onBack = viewModel::back)
    val versionGroup = state.map?.versionGroupIdentifier.orEmpty()

    Box(modifier.fillMaxSize()) {
        // Changement de carte (entrée, étage, retour) : la nouvelle carte apparaît en fondu.
        Crossfade(targetState = state.mapState, animationSpec = tween(MAP_FADE_MS), label = "map") { mapState ->
            Box(Modifier.fillMaxSize()) {
                if (mapState == null) {
                    if (state.failed) {
                        Text(
                            stringResource(R.string.data_load_error),
                            modifier = Modifier.align(Alignment.Center).padding(24.dp)
                        )
                    } else {
                        CircularProgressIndicator(Modifier.align(Alignment.Center))
                    }
                } else {
                    MapUI(Modifier.fillMaxSize(), state = mapState)
                }
            }
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
        // Étages du bâtiment : ils glissent depuis le bord en entrant, restent en place d'un étage à l'autre.
        AnimatedContent(
            targetState = state.floors,
            transitionSpec = {
                (fadeIn() + slideInHorizontally { it }) togetherWith (fadeOut() + slideOutHorizontally { it })
            },
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = FLOORS_TOP, end = 8.dp),
            label = "floors"
        ) { floors ->
            if (floors.isNotEmpty()) FloorSelector(floors, state.map?.id, viewModel::selectFloor)
        }
        Column(Modifier.align(Alignment.BottomCenter)) {
            state.highlight?.let { highlight ->
                HighlightBanner(highlight, onOpen = viewModel::openPlace, onClose = viewModel::clearHighlight)
            }
            val bottom = state.detail?.let { BottomCard.Detail(it) } ?: state.zone?.let { BottomCard.Zone(it) }
            AnimatedContent(
                targetState = bottom,
                contentKey = { it?.key },
                transitionSpec = {
                    (slideInVertically { it / 2 } + fadeIn()) togetherWith (slideOutVertically { it / 2 } + fadeOut())
                },
                label = "bottom"
            ) { card ->
                when (card) {
                    is BottomCard.Detail -> DetailCard(
                        detail = card.detail,
                        versionGroupIdentifier = versionGroup,
                        animated = state.animatedSprites,
                        onClose = viewModel::dismissDetail,
                        onOpenPokemon = onOpenPokemon,
                        onOpenItem = onOpenItem
                    )

                    is BottomCard.Zone -> ZoneBar(
                        zone = card.zone,
                        caught = state.caught,
                        closable = isWorld,
                        onOpenList = viewModel::openZoneList,
                        onClose = viewModel::clearZone
                    )

                    null -> Box(Modifier.fillMaxWidth())
                }
            }
            SnackbarHost(snackbar)
        }
    }

    val zone = state.zone
    if (state.zoneListOpen && zone != null) {
        ZoneListSheet(
            zone = zone,
            caught = state.caught,
            animated = state.animatedSprites,
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
                val parent = state.parent
                if (parent != null) {
                    IconButton(onClick = onBack) {
                        Icon(painterResource(R.drawable.ic_back), stringResource(R.string.map_back_to, parent.name))
                    }
                } else {
                    Box(Modifier.size(12.dp))
                }
                AnimatedContent(targetState = map.name, label = "title") { name ->
                    Text(
                        name,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(vertical = 10.dp)
                    )
                }
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
private fun ZoneBar(zone: MapZone, caught: Set<Int>, closable: Boolean, onOpenList: () -> Unit, onClose: () -> Unit) {
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
private fun ZoneListSheet(
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

private val MapLayer.label: Int
    get() = when (this) {
        MapLayer.WARPS -> R.string.map_layer_warps
        MapLayer.ITEMS -> R.string.label_items
        MapLayer.TRAINERS -> R.string.map_layer_trainers
        MapLayer.NPCS -> R.string.label_characters
        MapLayer.STATIC_POKEMON -> R.string.map_layer_static_pokemon
        MapLayer.WILD_POKEMON -> R.string.label_wild_pokemon
    }

/** Carte en bas d'écran : fiche de l'élément touché, ou lieu sélectionné. */
private sealed interface BottomCard {
    /** Change quand on passe à un autre élément ou lieu (et non quand son contenu se charge). */
    val key: String

    data class Detail(val detail: MapDetail) : BottomCard {
        override val key: String
            get() = when (detail) {
                is MapDetail.WildPokemon -> "wild:${detail.pokemonId}"
                is MapDetail.Item -> "object:${detail.obj.id}"
                is MapDetail.Character -> "object:${detail.obj.id}"
            }
    }

    data class Zone(val zone: MapZone) : BottomCard {
        override val key: String get() = "zone:${zone.mapId}"
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

/** Étages du bâtiment ou de la grotte, de haut en bas, comme les boutons d'un ascenseur. */
@Composable
private fun FloorSelector(floors: List<MapFloor>, currentId: Int?, onSelect: (Int) -> Unit) {
    Surface(shape = MaterialTheme.shapes.extraLarge, tonalElevation = 3.dp, shadowElevation = 2.dp) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .heightIn(max = FLOORS_MAX_HEIGHT)
                .verticalScroll(rememberScrollState())
                .padding(4.dp)
        ) {
            floors.forEach { floor ->
                val selected = floor.mapId == currentId
                val background by animateColorAsState(
                    if (selected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent,
                    label = "floor"
                )
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(FLOOR_SIZE)
                        .clip(CircleShape)
                        .background(background)
                        .clickable(enabled = !selected) { onSelect(floor.mapId) }
                ) {
                    Text(
                        floorLabel(floor.level),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                        color = if (selected) {
                            MaterialTheme.colorScheme.onPrimaryContainer
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun floorLabel(level: FloorLevel): String = when (level) {
    is FloorLevel.Storey -> if (level.number == 0) {
        stringResource(R.string.map_floor_ground)
    } else {
        stringResource(R.string.map_floor_storey, level.number)
    }

    is FloorLevel.Basement -> stringResource(R.string.map_floor_basement, level.number)

    FloorLevel.Roof -> stringResource(R.string.map_floor_roof)

    FloorLevel.Elevator -> stringResource(R.string.map_floor_elevator)
}

private const val MAP_FADE_MS = 300
private val LIST_ICON_WIDTH = 112.dp
private val PROGRESS_ICON = 24.dp
private val FLOOR_SIZE = 40.dp
private val FLOORS_TOP = 72.dp
private val FLOORS_MAX_HEIGHT = 360.dp
private val COMPLETE_COLOR = Color(0xFF43A047)
