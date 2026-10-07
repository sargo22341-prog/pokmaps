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
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.usecase.PlacePage
import org.opensources.pokmaps.ui.common.CaughtProgress
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.RoleIcons
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.common.SpriteSize
import org.opensources.pokmaps.ui.common.offersSummary

@Composable
fun PlaceRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PlaceViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    PlaceScreen(
        state,
        onAction = { action ->
            viewModel.onAction(action)
            when (action) {
                PlaceAction.ShowPlace, is PlaceAction.ShowObject -> onShowOnMap()
            }
        },
        onOpenPokemon = onOpenPokemon,
        onOpenItem = onOpenItem,
        onOpenPlace = onOpenPlace,
        onOpenCharacter = onOpenCharacter,
        modifier = modifier
    )
}

@Composable
fun PlaceScreen(
    state: PlaceUiState,
    onAction: (PlaceAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.place_not_found), modifier, state.failed)
        return
    }
    val onShowObject = { objectId: Int -> onAction(PlaceAction.ShowObject(objectId)) }
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        PlaceHeader(state, page) { onAction(PlaceAction.ShowPlace) }
        SheetSection(stringResource(R.string.label_wild_pokemon)) {
            if (state.encounterGroups.isEmpty()) {
                Text(stringResource(R.string.map_no_encounter), color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                EncounterGroups(
                    state.encounterGroups,
                    title = { it.pokemonName },
                    spritePlace = SpritePlace.SHEETS,
                    spriteSize = SpriteSize.SHEET,
                    caught = { it.pokemonId in state.caught },
                    onClick = { onOpenPokemon(it.pokemonId) }
                )
            }
        }
        ItemsSection(page, onOpenItem, onShowObject)
        CharactersSection(page, onOpenPokemon, onOpenCharacter, onShowObject)
        PlacesSection(page, onOpenPlace)
        Spacer(Modifier.height(24.dp))
    }
}

/** Nom du lieu, capture de ses Pokémon sauvages (« 1/3 », ou terminé) et bouton « Voir sur la carte ». */
@Composable
private fun PlaceHeader(state: PlaceUiState, page: PlacePage, onShowPlace: () -> Unit) {
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
        if (state.wildIds.isNotEmpty()) CaughtProgress(caught = state.caughtWild, total = state.wildIds.size)
        Button(onClick = onShowPlace) {
            Icon(
                painterResource(R.drawable.ic_map),
                contentDescription = null,
                modifier = Modifier.padding(end = 8.dp)
            )
            Text(stringResource(R.string.show_on_map))
        }
    }
}

/** Objets posés dans le lieu, visibles ou cachés. */
@Composable
private fun ItemsSection(page: PlacePage, onOpenItem: (String) -> Unit, onShowObject: (Int) -> Unit) {
    if (page.items.isEmpty()) return
    SheetSection(stringResource(R.string.label_items)) {
        page.items.forEach { obj ->
            val identifier = obj.itemIdentifier
            SheetRow(
                title = obj.itemName.orEmpty(),
                subtitle = stringResource(
                    if (obj.kind == MapObjectKind.HIDDEN_ITEM) R.string.map_hidden_item else R.string.map_item
                ),
                onClick = identifier?.let { { onOpenItem(it) } },
                onShowOnMap = { onShowObject(obj.id) },
                content = {
                    if (identifier != null) {
                        PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 48.dp, null)
                    }
                }
            )
        }
    }
}

/** Dresseurs, personnages et Pokémon fixes du lieu. */
@Composable
private fun CharactersSection(
    page: PlacePage,
    onOpenPokemon: (Int) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowObject: (Int) -> Unit
) {
    if (page.characters.isEmpty()) return
    val versionGroup = page.game.versionGroupIdentifier
    SheetSection(stringResource(R.string.label_characters)) {
        page.characters.forEach { obj ->
            val pokemonId = obj.pokemonId?.takeIf { obj.kind == MapObjectKind.POKEMON }
            SheetRow(
                title = obj.name,
                subtitle = if (obj.kind == MapObjectKind.POKEMON) {
                    stringResource(R.string.map_static_pokemon, obj.level ?: 0)
                } else {
                    offersSummary(page.offers[obj.id].orEmpty(), page.fossilUses)
                },
                onClick = {
                    if (pokemonId != null) onOpenPokemon(pokemonId) else onOpenCharacter(obj.id)
                },
                onShowOnMap = { onShowObject(obj.id) },
                labels = { RoleIcons(page.rolesOf(obj)) },
                content = {
                    if (pokemonId != null) {
                        PokemonSprite(pokemonId, SpritePlace.SHEETS, SpriteSize.SHEET, contentDescription = null)
                    } else {
                        CharacterSprite(obj, versionGroup)
                    }
                }
            )
        }
    }
}

/** Lieux accessibles depuis celui-ci (bâtiments, grottes, étages, sorties). */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PlacesSection(page: PlacePage, onOpenPlace: (String) -> Unit) {
    if (page.places.isEmpty()) return
    SheetSection(stringResource(R.string.map_places)) {
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            page.places.forEach { place ->
                FilledTonalButton(onClick = { onOpenPlace(place.identifier) }) { Text(place.name) }
            }
        }
    }
}
