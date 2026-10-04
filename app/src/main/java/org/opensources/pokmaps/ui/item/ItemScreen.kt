package org.opensources.pokmaps.ui.item

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.usecase.ItemPage
import org.opensources.pokmaps.domain.usecase.ItemSource
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.map.CharacterSprite
import org.opensources.pokmaps.ui.map.MoveLine
import org.opensources.pokmaps.ui.map.displayName

@Composable
fun ItemScreen(
    onOpenPokemon: (Int) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ItemViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.item_not_found), modifier)
        return
    }
    ItemContent(
        page,
        onOpenPokemon = onOpenPokemon,
        onOpenCharacter = onOpenCharacter,
        onShowOnMap = { objectId ->
            viewModel.showOnMap(objectId)
            onShowOnMap()
        },
        modifier = modifier
    )
}

@Composable
private fun ItemContent(
    page: ItemPage,
    onOpenPokemon: (Int) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val item = page.item
    val details = page.details
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
            if (item.hasSprite) PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 96.dp, item.name)
            Text(item.name, style = MaterialTheme.typography.headlineMedium)
            details?.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
        }
        details?.move?.let { move ->
            SheetSection(stringResource(R.string.map_machine_move, move.name)) { MoveLine(move) }
        }
        if (page.evolutions.isNotEmpty()) {
            SheetSection(stringResource(R.string.item_evolutions)) {
                page.evolutions.forEach { evolution ->
                    SheetRow(
                        title = stringResource(R.string.item_evolution, evolution.fromName, evolution.toName),
                        onClick = { onOpenPokemon(evolution.toId) },
                        image = {
                            PixelArtImage(Sprites.pokemonIcon(evolution.toId), PixelArt.POKEMON_ICON, 52.dp, null)
                        }
                    )
                }
            }
        }
        if (page.found.isNotEmpty()) {
            SheetSection(stringResource(R.string.item_found)) {
                page.found.forEach { source ->
                    SheetRow(
                        title = source.mapName,
                        subtitle = if (source.obj.kind == MapObjectKind.HIDDEN_ITEM) {
                            stringResource(R.string.map_hidden_item)
                        } else {
                            stringResource(R.string.map_item)
                        },
                        onShowOnMap = { onShowOnMap(source.obj.id) },
                        image = {
                            PixelArtImage(
                                Sprites.item(item.identifier),
                                PixelArt.ITEM_ICON,
                                48.dp,
                                null,
                                alpha = if (source.obj.kind == MapObjectKind.HIDDEN_ITEM) HIDDEN_ALPHA else 1f
                            )
                        }
                    )
                }
            }
        }
        if (page.sold.isNotEmpty()) {
            SheetSection(stringResource(R.string.item_sold)) {
                page.sold.forEach { source ->
                    SourceRow(source, versionGroup, onOpenCharacter, onShowOnMap) {
                        source.price?.let { stringResource(R.string.map_offer_price, it) }
                    }
                }
            }
        }
        if (page.given.isNotEmpty()) {
            SheetSection(stringResource(R.string.item_given)) {
                page.given.forEach { source ->
                    SourceRow(source, versionGroup, onOpenCharacter, onShowOnMap) {
                        source.quantity?.takeIf { it > 1 }?.let { "× $it" }
                    }
                }
            }
        }
        if (page.found.isEmpty() && page.sold.isEmpty() && page.given.isEmpty()) {
            SheetSection(stringResource(R.string.item_where)) {
                Text(stringResource(R.string.item_nowhere, page.game.name))
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

/** Personnage qui vend ou donne l'objet : sa fiche au toucher, sa position sur la carte avec le bouton. */
@Composable
private fun SourceRow(
    source: ItemSource,
    versionGroup: String,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: (Int) -> Unit,
    trailing: @Composable () -> String?
) {
    SheetRow(
        title = source.mapName,
        subtitle = source.obj.displayName(),
        trailing = trailing(),
        onClick = { onOpenCharacter(source.obj.id) },
        onShowOnMap = { onShowOnMap(source.obj.id) },
        image = { CharacterSprite(source.obj, versionGroup) }
    )
}

private const val HIDDEN_ALPHA = 0.6f
