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
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.usecase.ItemPage
import org.opensources.pokmaps.domain.usecase.ItemSource
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.MoveLine
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection

@Composable
fun ItemRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ItemViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ItemScreen(
        state,
        onAction = { action ->
            viewModel.onAction(action)
            when (action) {
                is ItemAction.ShowOnMap -> onShowOnMap()
            }
        },
        onOpenPokemon = onOpenPokemon,
        onOpenCharacter = onOpenCharacter,
        modifier = modifier
    )
}

@Composable
fun ItemScreen(
    state: ItemUiState,
    onAction: (ItemAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.item_not_found), modifier, state.failed)
        return
    }
    val onShowOnMap = { objectId: Int -> onAction(ItemAction.ShowOnMap(objectId)) }
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        ItemHeader(page)
        page.details?.move?.let { move ->
            SheetSection(stringResource(R.string.map_machine_move, move.name)) { MoveLine(move) }
        }
        EvolutionsSection(page, onOpenPokemon)
        FoundSection(page, onShowOnMap)
        SourcesSection(page, onOpenCharacter, onShowOnMap)
        if (page.found.isEmpty() && page.sold.isEmpty() && page.given.isEmpty()) {
            SheetSection(stringResource(R.string.item_where)) {
                Text(stringResource(R.string.item_nowhere, page.game.name))
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun ItemHeader(page: ItemPage) {
    val item = page.item
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        if (item.hasSprite) PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 96.dp, item.name)
        Text(item.name, style = MaterialTheme.typography.headlineMedium)
        page.details?.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
    }
}

/** Évolutions déclenchées par l'objet (pierres, échange en le tenant). */
@Composable
private fun EvolutionsSection(page: ItemPage, onOpenPokemon: (Int) -> Unit) {
    if (page.evolutions.isEmpty()) return
    SheetSection(stringResource(R.string.item_evolutions)) {
        page.evolutions.forEach { evolution ->
            SheetRow(
                title = stringResource(R.string.item_evolution, evolution.fromName, evolution.toName),
                onClick = { onOpenPokemon(evolution.toId) },
                content = {
                    PixelArtImage(Sprites.pokemonIcon(evolution.toId), PixelArt.POKEMON_ICON, 52.dp, null)
                }
            )
        }
    }
}

/** Exemplaires posés sur les cartes, visibles ou cachés. */
@Composable
private fun FoundSection(page: ItemPage, onShowOnMap: (Int) -> Unit) {
    if (page.found.isEmpty()) return
    SheetSection(stringResource(R.string.item_found)) {
        page.found.forEach { source ->
            val hidden = source.obj.kind == MapObjectKind.HIDDEN_ITEM
            SheetRow(
                title = source.mapName,
                subtitle = stringResource(if (hidden) R.string.map_hidden_item else R.string.map_item),
                onShowOnMap = { onShowOnMap(source.obj.id) },
                content = {
                    PixelArtImage(
                        Sprites.item(page.item.identifier),
                        PixelArt.ITEM_ICON,
                        48.dp,
                        null,
                        alpha = if (hidden) HIDDEN_ALPHA else 1f
                    )
                }
            )
        }
    }
}

/** Personnages qui vendent ou donnent l'objet. */
@Composable
private fun SourcesSection(page: ItemPage, onOpenCharacter: (Int) -> Unit, onShowOnMap: (Int) -> Unit) {
    val versionGroup = page.game.versionGroupIdentifier
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
}

/** Personnage qui vend ou donne l'objet : sa fiche au toucher, sa position sur la carte avec le bouton. */
@Composable
private fun SourceRow(
    source: ItemSource,
    versionGroup: String,
    onOpenCharacter: (Int) -> Unit,
    onShowOnMap: (Int) -> Unit,
    content: @Composable () -> String?
) {
    SheetRow(
        title = source.mapName,
        subtitle = source.obj.name,
        trailing = content(),
        onClick = { onOpenCharacter(source.obj.id) },
        onShowOnMap = { onShowOnMap(source.obj.id) },
        content = { CharacterSprite(source.obj, versionGroup) }
    )
}

private const val HIDDEN_ALPHA = 0.6f
