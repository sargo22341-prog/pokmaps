package org.opensources.pokmaps.ui.pokedex

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokedex.CaughtFilter
import org.opensources.pokmaps.ui.common.AnimatedPokemonSprite
import org.opensources.pokmaps.ui.common.CaughtButton
import org.opensources.pokmaps.ui.common.FavoriteButton
import org.opensources.pokmaps.ui.common.LocalAnimatedSprites
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtFill
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.label

@Composable
fun PokedexScreen(
    onOpenPokemon: (Int) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PokedexViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }
    if (state.failed) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(stringResource(R.string.data_load_error), textAlign = TextAlign.Center)
        }
        return
    }
    Column(modifier.fillMaxSize()) {
        SearchField(state.filter.query, viewModel::search)
        Filters(state, viewModel)
        Text(
            pluralStringResource(
                R.plurals.pokedex_count_caught,
                state.entries.size,
                state.entries.size,
                state.caughtCount,
                state.total
            ),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
        )
        if (state.entries.isEmpty()) {
            Text(
                stringResource(R.string.pokedex_empty),
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(32.dp)
            )
        } else {
            PokedexGrid(
                state.entries,
                onOpenPokemon = onOpenPokemon,
                onToggleCaught = viewModel::toggleCaught,
                onToggleFavorite = viewModel::toggleFavorite
            )
        }
    }
}

@Composable
private fun SearchField(query: String, onQueryChange: (String) -> Unit) {
    OutlinedTextField(
        value = query,
        onValueChange = onQueryChange,
        placeholder = { Text(stringResource(R.string.pokedex_search)) },
        leadingIcon = { Icon(painterResource(R.drawable.ic_search), contentDescription = null) },
        trailingIcon = {
            if (query.isNotEmpty()) {
                IconButton(onClick = { onQueryChange("") }) {
                    Icon(painterResource(R.drawable.ic_close), stringResource(R.string.pokedex_clear_search))
                }
            }
        },
        singleLine = true,
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
    )
}

@Composable
private fun Filters(state: PokedexUiState, viewModel: PokedexViewModel) {
    val filter = state.filter
    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 16.dp)
    ) {
        FilterChip(
            selected = filter.availableOnly,
            onClick = viewModel::toggleAvailableOnly,
            label = { Text(stringResource(R.string.pokedex_filter_available, state.game?.name.orEmpty())) }
        )
        DropdownChip(
            label = state.types.firstOrNull { it.id == filter.typeId }?.name
                ?: stringResource(R.string.pokedex_filter_type),
            selected = filter.typeId != null,
            options = listOf(null to stringResource(R.string.pokedex_filter_all)) +
                state.types.map { it.id to it.name },
            onSelect = viewModel::filterType
        )
        DropdownChip(
            label = filter.method?.let { stringResource(it.label) } ?: stringResource(R.string.pokedex_filter_method),
            selected = filter.method != null,
            options = listOf(null to stringResource(R.string.pokedex_filter_all)) +
                ObtainMethod.entries.map { it to stringResource(it.label) },
            onSelect = viewModel::filterMethod
        )
        DropdownChip(
            label = stringResource(
                if (filter.caught == CaughtFilter.ALL) R.string.pokedex_filter_capture else filter.caught.label
            ),
            selected = filter.caught != CaughtFilter.ALL,
            options = CaughtFilter.entries.map { it to stringResource(it.label) },
            onSelect = viewModel::filterCaught
        )
        FilterChip(
            selected = filter.favoritesOnly,
            onClick = viewModel::toggleFavoritesOnly,
            label = { Text(stringResource(R.string.pokedex_filter_favorites)) },
            leadingIcon = { Icon(painterResource(R.drawable.ic_star), contentDescription = null) }
        )
        if (filter.isActive) {
            TextButton(onClick = viewModel::resetFilters) { Text(stringResource(R.string.pokedex_filter_reset)) }
        }
    }
}

@Composable
private fun <T> DropdownChip(label: String, selected: Boolean, options: List<Pair<T, String>>, onSelect: (T) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        FilterChip(
            selected = selected,
            onClick = { expanded = true },
            label = { Text(label) },
            trailingIcon = { Icon(painterResource(R.drawable.ic_arrow_down), contentDescription = null) }
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (value, text) ->
                DropdownMenuItem(
                    text = { Text(text) },
                    onClick = {
                        expanded = false
                        onSelect(value)
                    }
                )
            }
        }
    }
}

@Composable
private fun PokedexGrid(
    entries: List<PokedexEntry>,
    onOpenPokemon: (Int) -> Unit,
    onToggleCaught: (PokedexEntry) -> Unit,
    onToggleFavorite: (PokedexEntry) -> Unit
) {
    LazyVerticalGrid(
        columns = GridCells.Adaptive(minSize = 160.dp),
        contentPadding = PaddingValues(12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        items(entries, key = { it.pokemonId }) { entry ->
            PokedexCard(
                entry,
                onClick = { onOpenPokemon(entry.pokemonId) },
                onToggleCaught = { onToggleCaught(entry) },
                onToggleFavorite = { onToggleFavorite(entry) }
            )
        }
    }
}

@Composable
private fun PokedexCard(
    entry: PokedexEntry,
    onClick: () -> Unit,
    onToggleCaught: () -> Unit,
    onToggleFavorite: () -> Unit
) {
    // Les Pokémon absents de la version restent visibles, estompés.
    val alpha = if (entry.isAvailable) 1f else UNAVAILABLE_ALPHA
    ElevatedCard(Modifier.clickable(onClick = onClick)) {
        Box {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(2.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp)
            ) {
                if (LocalAnimatedSprites.current) {
                    AnimatedPokemonSprite(
                        entry.pokemonId,
                        contentDescription = null,
                        alpha = alpha,
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(PixelArt.POKEMON_ICON.width / PixelArt.POKEMON_ICON.height.toFloat())
                    )
                } else {
                    PixelArtFill(
                        Sprites.pokemonIcon(entry.pokemonId),
                        PixelArt.POKEMON_ICON,
                        contentDescription = null,
                        alpha = alpha,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                Text(
                    stringResource(R.string.pokedex_number, entry.number),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    entry.name,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = alpha)
                )
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    entry.types.forEach { TypeBadge(it) }
                }
                if (!entry.isAvailable) {
                    Text(
                        stringResource(R.string.pokedex_unavailable),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                }
            }
            CaughtButton(entry.caught, onToggleCaught, Modifier.align(Alignment.TopStart))
            FavoriteButton(entry.favorite, onToggleFavorite, Modifier.align(Alignment.TopEnd))
        }
    }
}

private val CaughtFilter.label: Int
    get() = when (this) {
        CaughtFilter.ALL -> R.string.pokedex_filter_all
        CaughtFilter.CAUGHT -> R.string.pokedex_filter_caught
        CaughtFilter.MISSING -> R.string.pokedex_filter_missing
    }

private const val UNAVAILABLE_ALPHA = 0.45f
