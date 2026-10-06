package org.opensources.pokmaps.ui.place

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.usecase.PlacePage
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.map.CharacterSprite
import org.opensources.pokmaps.ui.map.displayName
import org.opensources.pokmaps.ui.search.offersSummary

@Composable
fun PlaceScreen(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PlaceViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.place_not_found), modifier, state.failed)
        return
    }
    PlaceContent(
        page,
        onOpenPokemon = onOpenPokemon,
        onOpenItem = onOpenItem,
        onOpenPlace = onOpenPlace,
        onOpenCharacter = onOpenCharacter,
        onShowPlace = {
            viewModel.showOnMap()
            onShowOnMap()
        },
        onShowObject = { objectId ->
            viewModel.showObjectOnMap(objectId)
            onShowOnMap()
        },
        modifier = modifier
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PlaceContent(
    page: PlacePage,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowPlace: () -> Unit,
    onShowObject: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val versionGroup = page.game.versionGroupIdentifier
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(page.map.name, style = MaterialTheme.typography.headlineMedium)
            Text(
                stringResource(if (page.map.parentId != null) R.string.place_outdoor else R.string.place_indoor),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Button(onClick = onShowPlace) {
                Icon(
                    painterResource(R.drawable.ic_map),
                    contentDescription = null,
                    modifier = Modifier.padding(end = 8.dp)
                )
                Text(stringResource(R.string.sheet_show_on_map))
            }
        }
        SheetSection(stringResource(R.string.place_wild)) {
            if (page.encounters.isEmpty()) {
                Text(stringResource(R.string.map_no_encounter), color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                EncounterGroups(
                    page.encounters.groupByMethod(),
                    title = { it.pokemonName },
                    iconPath = { Sprites.pokemonIcon(it.pokemonId) },
                    onClick = { onOpenPokemon(it.pokemonId) }
                )
            }
        }
        if (page.items.isNotEmpty()) {
            SheetSection(stringResource(R.string.place_items)) {
                page.items.forEach { obj ->
                    val identifier = obj.itemIdentifier
                    SheetRow(
                        title = obj.itemName.orEmpty(),
                        subtitle = stringResource(
                            if (obj.kind == MapObjectKind.HIDDEN_ITEM) R.string.map_hidden_item else R.string.map_item
                        ),
                        onClick = identifier?.let { { onOpenItem(it) } },
                        onShowOnMap = { onShowObject(obj.id) },
                        image = {
                            if (identifier != null) {
                                PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 48.dp, null)
                            }
                        }
                    )
                }
            }
        }
        if (page.characters.isNotEmpty()) {
            SheetSection(stringResource(R.string.place_characters)) {
                page.characters.forEach { obj ->
                    val pokemonId = obj.pokemonId
                    SheetRow(
                        title = obj.displayName(),
                        subtitle = when (obj.kind) {
                            MapObjectKind.TRAINER -> stringResource(R.string.map_trainer)
                            MapObjectKind.POKEMON -> stringResource(R.string.map_static_pokemon, obj.level ?: 0)
                            else -> offersSummary(page.offers[obj.id].orEmpty())
                        },
                        onClick = {
                            if (obj.kind == MapObjectKind.POKEMON && pokemonId != null) {
                                onOpenPokemon(pokemonId)
                            } else {
                                onOpenCharacter(obj.id)
                            }
                        },
                        onShowOnMap = { onShowObject(obj.id) },
                        image = {
                            if (obj.kind == MapObjectKind.POKEMON && pokemonId != null) {
                                PixelArtImage(Sprites.pokemonIcon(pokemonId), PixelArt.POKEMON_ICON, 52.dp, null)
                            } else {
                                CharacterSprite(obj, versionGroup)
                            }
                        }
                    )
                }
            }
        }
        if (page.places.isNotEmpty()) {
            SheetSection(stringResource(R.string.map_places)) {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    page.places.forEach { place ->
                        FilledTonalButton(onClick = { onOpenPlace(place.identifier) }) { Text(place.name) }
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}
