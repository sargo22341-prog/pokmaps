package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun BreedingSpeciesSelector(
    pokemonId: Int,
    name: String,
    state: BreedingUiState,
    first: Boolean,
    onAction: (BreedingAction) -> Unit,
    onPreview: (GuideTarget) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        ExposedDropdownMenuBox(
            expanded = expanded,
            onExpandedChange = {
                onAction(BreedingAction.Search(""))
                expanded = it
            },
            modifier = Modifier.weight(1f)
        ) {
            OutlinedTextField(
                value = if (expanded) state.query else name,
                onValueChange = { onAction(BreedingAction.Search(it)) },
                singleLine = true,
                label = { Text(stringResource(R.string.breeding_search)) },
                placeholder = { Text(name) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.menuAnchor(ExposedDropdownMenuAnchorType.PrimaryEditable).fillMaxWidth()
            )
            ExposedDropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false },
                modifier = Modifier.heightIn(max = 280.dp)
            ) {
                if (state.choices.isEmpty()) Text(stringResource(R.string.guide_empty))
                state.choices.forEach { entry ->
                    DropdownMenuItem(text = { Text(entry.name) }, onClick = {
                        expanded = false
                        onAction(BreedingAction.Species(first, entry.pokemonId))
                    })
                }
            }
        }
        BreedingPokemonSprite(pokemonId, name, onPreview)
    }
}

@Composable
internal fun BreedingPokemonSprite(id: Int, name: String, onPreview: (GuideTarget) -> Unit) {
    PokemonSprite(
        id,
        SpritePlace.SHEETS,
        SpriteSize.LIST,
        contentDescription = name,
        modifier = Modifier.clickable { onPreview(GuideTarget.Pokemon(id)) }
    )
}
