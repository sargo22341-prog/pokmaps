package org.opensources.pokmaps.ui.item

import androidx.annotation.StringRes
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.ItemEvolution
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.usecase.ItemPage
import org.opensources.pokmaps.domain.usecase.ItemSource
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.FossilRevivalLine
import org.opensources.pokmaps.ui.common.MoveEffectText
import org.opensources.pokmaps.ui.common.MoveLine
import org.opensources.pokmaps.ui.common.OfferLinks
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.common.SpriteSize

/** Fiches ouvertes depuis la fiche d'un objet : Pokémon, personnage, ou attaque enseignée par la CT / CS. */
data class ItemLinks(
    val onOpenPokemon: (Int) -> Unit,
    val onOpenCharacter: (Int) -> Unit,
    val onOpenMove: (Int) -> Unit
)

@Composable
fun ItemRoute(
    links: ItemLinks,
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
        links = links,
        modifier = modifier
    )
}

@Composable
fun ItemScreen(state: ItemUiState, onAction: (ItemAction) -> Unit, links: ItemLinks, modifier: Modifier = Modifier) {
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.item_not_found), modifier, state.failed)
        return
    }
    val onShowOnMap = { objectId: Int -> onAction(ItemAction.ShowOnMap(objectId)) }
    val sources = SourceLinks(page.game.versionGroupIdentifier, links.onOpenCharacter, onShowOnMap)
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        ItemHeader(page)
        MachineMoveSection(page, links.onOpenMove)
        EvolutionsSection(page, links.onOpenPokemon)
        FossilSection(page, sources, links.onOpenPokemon)
        FoundSection(page, onShowOnMap)
        SourcesSection(page, sources)
        ExchangesSection(page, sources)
        if (page.nowhere) {
            SheetSection(stringResource(R.string.item_where)) {
                Text(stringResource(R.string.item_nowhere, page.game.name))
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

/** Fiche et position sur la carte des personnages liés à l'objet. */
private data class SourceLinks(
    val versionGroup: String,
    val onOpenCharacter: (Int) -> Unit,
    val onShowOnMap: (Int) -> Unit
)

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

/** CT / CS : l'attaque enseignée, ce qu'elle fait (avec la probabilité de son effet) et un lien vers sa fiche. */
@Composable
private fun MachineMoveSection(page: ItemPage, onOpenMove: (Int) -> Unit) {
    val details = page.details ?: return
    val move = details.move ?: return
    SheetSection(stringResource(R.string.map_machine_move, move.name)) {
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClickLabel = stringResource(R.string.move_open)) { onOpenMove(move.moveId) }
                .padding(vertical = 4.dp)
        ) {
            MoveLine(move)
            details.moveEffect?.let { MoveEffectText(it) }
            Text(
                stringResource(R.string.move_open),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

/** Évolutions déclenchées par l'objet (pierres), comme une ligne d'évolution : Pokémon → évolution. */
@Composable
private fun EvolutionsSection(page: ItemPage, onOpenPokemon: (Int) -> Unit) {
    if (page.evolutions.isEmpty()) return
    SheetSection(stringResource(R.string.item_evolutions)) {
        page.evolutions.forEach { EvolutionLine(it, onOpenPokemon) }
    }
}

@Composable
private fun EvolutionLine(evolution: ItemEvolution, onOpenPokemon: (Int) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenPokemon(evolution.toId) }
            .padding(vertical = 4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PokemonSprite(evolution.fromId, SpritePlace.EVOLUTIONS, SpriteSize.SHEET, contentDescription = null)
            Text(stringResource(R.string.evolution_arrow), style = MaterialTheme.typography.titleLarge)
            PokemonSprite(evolution.toId, SpritePlace.EVOLUTIONS, SpriteSize.SHEET, contentDescription = null)
        }
        Text(
            stringResource(R.string.item_evolution, evolution.fromName, evolution.toName),
            style = MaterialTheme.typography.bodyLarge
        )
    }
}

/** Fossile : le Pokémon qu'il devient (comme une évolution), et le personnage qui le ranime. */
@Composable
private fun FossilSection(page: ItemPage, sources: SourceLinks, onOpenPokemon: (Int) -> Unit) {
    val fossil = page.fossil ?: return
    val item = page.item
    SheetSection(stringResource(R.string.item_fossil)) {
        FossilRevivalLine(
            fossil = OfferItem(item.id, item.identifier, item.name, item.hasSprite),
            pokemonId = fossil.pokemonId,
            text = stringResource(R.string.map_offer_pokemon_level, fossil.pokemonName, fossil.level),
            links = OfferLinks(SpritePlace.EVOLUTIONS, onOpenPokemon, onOpenItem = null)
        )
    }
    SheetSection(stringResource(R.string.item_fossil_where)) {
        SourceRow(ItemSource(fossil.reviver, fossil.reviverMapName), sources, trailing = null)
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

/** Personnages qui vendent, donnent ou font gagner l'objet (lots du Casino). */
@Composable
private fun SourcesSection(page: ItemPage, sources: SourceLinks) {
    SourceList(R.string.item_sold, page.sold, sources, SourceDetail.PRICE)
    SourceList(R.string.item_given, page.given, sources, SourceDetail.QUANTITY)
    SourceList(R.string.item_prizes, page.prizes, sources, SourceDetail.COINS)
}

/** Échanges d'objets : contre quoi on l'obtient, et ce qu'on obtient en le donnant. */
@Composable
private fun ExchangesSection(page: ItemPage, sources: SourceLinks) {
    SourceList(R.string.item_exchange_get, page.exchangedFor, sources, SourceDetail.WANTED_ITEM)
    SourceList(R.string.item_exchange_give, page.exchangeableFor, sources, SourceDetail.RECEIVED_ITEM)
}

/** Ce qu'affiche une source à droite : prix, quantité, jetons ou objet de l'échange. */
private enum class SourceDetail {
    PRICE,
    QUANTITY,
    COINS,
    WANTED_ITEM,
    RECEIVED_ITEM
}

@Composable
private fun SourceList(@StringRes title: Int, list: List<ItemSource>, sources: SourceLinks, detail: SourceDetail) {
    if (list.isEmpty()) return
    SheetSection(stringResource(title)) {
        list.forEach { source -> SourceRow(source, sources, detailText(source, detail)) }
    }
}

@Composable
private fun detailText(source: ItemSource, detail: SourceDetail): String? = when (detail) {
    SourceDetail.PRICE -> source.price?.let { stringResource(R.string.map_offer_price, it) }
    SourceDetail.QUANTITY -> source.quantity?.takeIf { it > 1 }?.let { "× $it" }
    SourceDetail.COINS -> source.price?.let { pluralStringResource(R.plurals.coins, it, it) }
    SourceDetail.WANTED_ITEM -> source.otherItemName?.let { stringResource(R.string.item_exchange_for, it) }
    SourceDetail.RECEIVED_ITEM -> source.otherItemName
}

/** Personnage lié à l'objet : sa fiche au toucher, sa position sur la carte avec le bouton. */
@Composable
private fun SourceRow(source: ItemSource, sources: SourceLinks, trailing: String?) {
    SheetRow(
        title = source.mapName,
        subtitle = source.obj.name,
        trailing = trailing,
        onClick = { sources.onOpenCharacter(source.obj.id) },
        onShowOnMap = { sources.onShowOnMap(source.obj.id) },
        content = { CharacterSprite(source.obj, sources.versionGroup) }
    )
}

private const val HIDDEN_ALPHA = 0.6f
