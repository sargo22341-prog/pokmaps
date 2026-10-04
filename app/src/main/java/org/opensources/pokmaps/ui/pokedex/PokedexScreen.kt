package org.opensources.pokmaps.ui.pokedex

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.PokedexEntry

@Composable
fun PokedexScreen(modifier: Modifier = Modifier, viewModel: PokedexViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
    } else {
        PokedexList(state.entries, modifier)
    }
}

@Composable
private fun PokedexList(entries: List<PokedexEntry>, modifier: Modifier = Modifier) {
    LazyColumn(modifier.fillMaxSize()) {
        items(entries, key = { it.pokemonId }) { entry ->
            ListItem(
                leadingContent = {
                    Text(
                        stringResource(R.string.pokedex_number, entry.number),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                },
                headlineContent = { Text(entry.name) }
            )
            HorizontalDivider()
        }
    }
}
