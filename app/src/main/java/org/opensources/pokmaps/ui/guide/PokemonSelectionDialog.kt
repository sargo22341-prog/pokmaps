package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@Composable
fun PokemonSelectionDialog(
    choices: List<PokedexEntry>,
    query: String,
    onQuery: (String) -> Unit,
    onClose: () -> Unit,
    onSelect: (Int) -> Unit
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(stringResource(R.string.breeding_choose)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = onQuery,
                    singleLine = true,
                    label = { Text(stringResource(R.string.breeding_search)) },
                    modifier = Modifier.fillMaxWidth()
                )
                if (choices.isEmpty()) Text(stringResource(R.string.guide_empty))
                LazyColumn(Modifier.heightIn(max = 360.dp)) {
                    items(choices, key = { it.pokemonId }) { entry ->
                        PokemonSelectionRow(entry) { onSelect(entry.pokemonId) }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.guide_close)) } }
    )
}

@Composable
private fun PokemonSelectionRow(entry: PokedexEntry, onSelect: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).clickable(onClick = onSelect)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        PokemonSprite(entry.pokemonId, SpritePlace.SHEETS, SpriteSize.LIST, contentDescription = null)
        Text(stringResource(R.string.pokedex_number, entry.number), color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(entry.name, style = MaterialTheme.typography.bodyLarge)
    }
}
