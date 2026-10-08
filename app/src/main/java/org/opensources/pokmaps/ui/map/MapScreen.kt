package org.opensources.pokmaps.ui.map

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
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
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize
import ovh.plrapps.mapcompose.ui.MapUI

@Composable
fun MapRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MapViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    // Retour sur la carte (après le Pokédex, une fiche…) : la carte est recréée pour que les touches remarchent,
    // puis les demandes en attente (« Voir sur la carte ») sont traitées.
    DisposableEffect(viewModel) {
        viewModel.onScreenShown()
        onDispose { viewModel.onScreenHidden() }
    }
    MapScreen(state, viewModel::onAction, onOpenPokemon, onOpenItem, modifier)
}

@Composable
fun MapScreen(
    state: MapUiState,
    onAction: (MapAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val snackbar = remember { SnackbarHostState() }
    MessageEffect(state, snackbar, onAction)
    // Retour : vers le niveau du dessus (bâtiment, ville ou route), ou désélection du lieu sur la carte du monde.
    val isWorld = state.map?.isWorld == true
    BackHandler(enabled = state.parent != null || (isWorld && state.zone != null)) { onAction(MapAction.Back) }

    Box(modifier.fillMaxSize()) {
        MapCanvas(state)
        MapToolbar(state, onAction)
        Floors(state, onAction)
        BottomPanel(state, snackbar, onAction, onOpenPokemon, onOpenItem)
    }

    MapZoneSheet(state, onAction, onOpenPokemon, onOpenItem)
}

@Composable
private fun BoxScope.MapToolbar(state: MapUiState, onAction: (MapAction) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .align(Alignment.TopStart)
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        if (state.worlds.size > 1) {
            WorldSelector(state, onAction, Modifier.weight(1f))
        } else {
            MapTitle(state, onBack = { onAction(MapAction.Back) }, Modifier.weight(1f))
        }
        if ((state.game?.generationId ?: 0) >= 2) {
            TimeButton(state.time, iconOnly = true) { onAction(MapAction.CycleTime) }
        }
        LayersButton(state.layers) { onAction(MapAction.ToggleLayer(it)) }
    }
}

@Composable
private fun MapZoneSheet(
    state: MapUiState,
    onAction: (MapAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    val zone = state.zone
    if (state.zoneListOpen && zone != null) {
        ZoneListSheet(
            zone = zone,
            timed = (state.game?.generationId ?: 0) >= 2,
            initialTime = state.time,
            caught = state.caught,
            onDismiss = { onAction(MapAction.CloseZoneList) },
            onOpenPlace = { onAction(MapAction.OpenPlace(it)) },
            onOpenPokemon = { id ->
                onAction(MapAction.CloseZoneList)
                onOpenPokemon(id)
            },
            onOpenItem = { identifier ->
                onAction(MapAction.CloseZoneList)
                onOpenItem(identifier)
            },
            onShowObject = { id ->
                onAction(MapAction.CloseZoneList)
                onAction(MapAction.FocusObject(id))
            }
        )
    }
}

/** Affiche une fois le message de l'état (Pokémon introuvable, lieux illisibles). */
@Composable
private fun MessageEffect(state: MapUiState, snackbar: SnackbarHostState, onAction: (MapAction) -> Unit) {
    val text = when (val message = state.message) {
        null -> null

        is MapMessage.NotFound ->
            stringResource(R.string.map_highlight_none, message.pokemonName, state.game?.name.orEmpty())

        is MapMessage.HighlightFailed -> stringResource(R.string.map_highlight_error, message.pokemonName)
    }
    LaunchedEffect(text) {
        if (text != null) {
            onAction(MapAction.MessageShown)
            snackbar.showSnackbar(text)
        }
    }
}

/** Carte MapCompose ; un changement de carte (entrée, étage, retour) la fait apparaître en fondu. */
@Composable
private fun MapCanvas(state: MapUiState) {
    Crossfade(targetState = state.mapState, animationSpec = tween(MAP_FADE_MS), label = "map") { mapState ->
        Box(Modifier.fillMaxSize()) {
            when {
                mapState != null -> {
                    MapUI(Modifier.fillMaxSize(), state = mapState)
                    if ((state.game?.generationId ?: 0) >= 2) MapDaylight(state.time)
                }

                state.failed -> Text(
                    stringResource(R.string.data_load_error),
                    modifier = Modifier.align(Alignment.Center).padding(24.dp)
                )

                state.game != null -> Text(
                    stringResource(R.string.map_empty),
                    modifier = Modifier.align(Alignment.Center).padding(24.dp)
                )

                else -> CircularProgressIndicator(Modifier.align(Alignment.Center))
            }
        }
    }
}

/** Étages du bâtiment : ils glissent depuis le bord en entrant, restent en place d'un étage à l'autre. */
@Composable
private fun BoxScope.Floors(state: MapUiState, onAction: (MapAction) -> Unit) {
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
        if (floors.isNotEmpty()) FloorSelector(floors, state.map?.id) { onAction(MapAction.SelectFloor(it)) }
    }
}

/** Bas de l'écran : surlignage en cours, fiche de l'élément touché ou lieu sélectionné, messages. */
@Composable
private fun BoxScope.BottomPanel(
    state: MapUiState,
    snackbar: SnackbarHostState,
    onAction: (MapAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    Column(Modifier.align(Alignment.BottomCenter)) {
        state.highlight?.let { highlight ->
            HighlightBanner(
                highlight,
                onOpen = { onAction(MapAction.OpenPlace(it)) },
                onClose = { onAction(MapAction.ClearHighlight) }
            )
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
                    versionGroupIdentifier = state.map?.versionGroupIdentifier.orEmpty(),
                    onClose = { onAction(MapAction.DismissDetail) },
                    onOpenPokemon = onOpenPokemon,
                    onOpenItem = onOpenItem,
                    onShowObject = { onAction(MapAction.FocusObject(it)) }
                )

                is BottomCard.Zone -> ZoneBar(
                    zone = card.zone,
                    caught = state.caught,
                    closable = state.map?.isWorld == true,
                    onOpenList = { onAction(MapAction.OpenZoneList) },
                    onClose = { onAction(MapAction.ClearZone) }
                )

                null -> Box(Modifier.fillMaxWidth())
            }
        }
        SnackbarHost(snackbar)
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
                PokemonSprite(highlight.pokemonId, SpritePlace.MAP_LIST, SpriteSize.SMALL, contentDescription = null)
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

private const val MAP_FADE_MS = 300
private val FLOORS_TOP = 72.dp
