package org.opensources.pokmaps.ui.search

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SheetSection
import org.opensources.pokmaps.ui.common.offersSummary

@Composable
fun SearchRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SearchViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    SearchScreen(state, viewModel::onAction, onOpenPokemon, onOpenItem, onOpenPlace, onOpenCharacter, modifier)
}

@Composable
fun SearchScreen(
    state: SearchUiState,
    onAction: (SearchAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onOpenCharacter: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    Column(modifier.fillMaxSize()) {
        OutlinedTextField(
            value = state.query,
            onValueChange = { onAction(SearchAction.Query(it)) },
            placeholder = { Text(stringResource(R.string.search_hint)) },
            leadingIcon = { Icon(painterResource(R.drawable.ic_search), contentDescription = null) },
            trailingIcon = {
                if (state.query.isNotEmpty()) {
                    IconButton(onClick = { onAction(SearchAction.Query("")) }) {
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
            state.loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }

            state.failed -> Message(stringResource(R.string.data_load_error))

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
        section(R.string.search_pokemon, state.pokemon, key = { "pokemon:${it.pokemonId}" }) { entry ->
            SheetRow(
                title = entry.name,
                subtitle = stringResource(R.string.pokedex_number, entry.number),
                onClick = { onOpenPokemon(entry.pokemonId) },
                content = { PixelArtImage(Sprites.pokemonIcon(entry.pokemonId), PixelArt.POKEMON_ICON, 52.dp, null) }
            )
        }
        section(R.string.search_places, state.places, key = { "place:${it.identifier}" }) { place ->
            SheetRow(
                title = place.name,
                subtitle = stringResource(if (place.outdoor) R.string.place_outdoor else R.string.place_indoor),
                onClick = { onOpenPlace(place.identifier) },
                content = { Icon(painterResource(R.drawable.ic_place), contentDescription = null) }
            )
        }
        section(R.string.search_items, state.items, key = { "item:${it.identifier}" }) { item ->
            SheetRow(
                title = item.name,
                subtitle = item.moveName,
                onClick = { onOpenItem(item.identifier) },
                content = {
                    if (item.hasSprite) {
                        PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 48.dp, null)
                    }
                }
            )
        }
        section(R.string.search_characters, state.characters, key = { "character:${it.obj.id}" }) { character ->
            SheetRow(
                title = character.name,
                subtitle = listOf(character.mapName, offersSummary(character.offers))
                    .filter { it.isNotEmpty() }
                    .joinToString(" · "),
                onClick = { onOpenCharacter(character.obj.id) },
                content = { CharacterSprite(character.obj, versionGroup) }
            )
        }
    }
}

/** Section de résultats ; `key` identifie un résultat de façon unique dans toute la liste. */
private fun <T> LazyListScope.section(title: Int, results: List<T>, key: (T) -> String, row: @Composable (T) -> Unit) {
    if (results.isEmpty()) return
    item(key = "title:$title") {
        SheetSection(stringResource(title, results.size)) {}
    }
    items(results, key = key) { result ->
        Column(Modifier.padding(horizontal = 16.dp)) { row(result) }
    }
}
