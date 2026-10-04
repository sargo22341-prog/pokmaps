package org.opensources.pokmaps.ui.search

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.map.CharacterSprite

@Composable
fun SearchScreen(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SearchViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    Column(modifier.fillMaxSize()) {
        OutlinedTextField(
            value = state.query,
            onValueChange = viewModel::search,
            placeholder = { Text(stringResource(R.string.search_hint)) },
            leadingIcon = { Icon(painterResource(R.drawable.ic_search), contentDescription = null) },
            trailingIcon = {
                if (state.query.isNotEmpty()) {
                    IconButton(onClick = { viewModel.search("") }) {
                        Icon(painterResource(R.drawable.ic_close), stringResource(R.string.pokedex_clear_search))
                    }
                }
            },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .focusRequester(focus)
        )
        when {
            state.query.isBlank() -> Message(stringResource(R.string.search_intro, state.game?.name.orEmpty()))
            state.isEmpty -> Message(stringResource(R.string.search_empty))
            else -> Results(state, onOpenPokemon, onOpenItem, onOpenPlace, onOpenCharacter)
        }
    }
}

@Composable
private fun Message(text: String) {
    Text(
        text,
        textAlign = TextAlign.Center,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier
            .fillMaxWidth()
            .padding(32.dp)
    )
}

@Composable
private fun Results(
    state: SearchUiState,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit
) {
    val versionGroup = state.game?.versionGroupIdentifier.orEmpty()
    LazyColumn(Modifier.fillMaxSize()) {
        section(R.string.search_pokemon, state.pokemon) { entry ->
            SheetRow(
                title = entry.name,
                subtitle = stringResource(R.string.pokedex_number, entry.number),
                onClick = { onOpenPokemon(entry.pokemonId) },
                image = { PixelArtImage(Sprites.pokemonIcon(entry.pokemonId), PixelArt.POKEMON_ICON, 52.dp, null) }
            )
        }
        section(R.string.search_places, state.places) { place ->
            SheetRow(
                title = place.name,
                subtitle = stringResource(if (place.outdoor) R.string.place_outdoor else R.string.place_indoor),
                onClick = { onOpenPlace(place.identifier) },
                image = { Icon(painterResource(R.drawable.ic_place), contentDescription = null) }
            )
        }
        section(R.string.search_items, state.items) { item ->
            SheetRow(
                title = item.name,
                subtitle = item.moveName,
                onClick = { onOpenItem(item.identifier) },
                image = {
                    if (item.hasSprite) {
                        PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 48.dp, null)
                    }
                }
            )
        }
        section(R.string.search_characters, state.characters) { character ->
            SheetRow(
                title = character.name,
                subtitle = listOf(character.mapName, offersSummary(character.offers))
                    .filter { it.isNotEmpty() }
                    .joinToString(" · "),
                onClick = { onOpenCharacter(character.obj.id) },
                image = { CharacterSprite(character.obj, versionGroup) }
            )
        }
    }
}

private fun <T> LazyListScope.section(title: Int, results: List<T>, row: @Composable (T) -> Unit) {
    if (results.isEmpty()) return
    item(key = "title:$title") {
        SheetSection(stringResource(title, results.size)) {}
    }
    items(results) { result ->
        Column(Modifier.padding(horizontal = 16.dp)) { row(result) }
    }
}

/** « Donne CT28 · Vend Poké Ball, Potion · Échange Lippoutou » */
@Composable
fun offersSummary(offers: List<OfferLink>): String {
    fun names(kind: String, name: (OfferLink) -> String?) =
        offers.filter { it.kind == kind }.mapNotNull(name).distinct().joinToString(", ")

    val gifts = offers.mapNotNull {
        when (it.kind) {
            OfferLink.GIFT_ITEM -> it.itemName
            OfferLink.GIFT_POKEMON -> it.pokemonName
            else -> null
        }
    }.distinct().joinToString(", ")
    val sales = names(OfferLink.SALE) { it.itemName }
    val trades = names(OfferLink.TRADE) { it.pokemonName }
    return listOfNotNull(
        gifts.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_gifts, it) },
        sales.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_sales, it) },
        trades.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_trades, it) }
    ).joinToString(" · ")
}
