package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

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
        OutlinedButton(onClick = {
            onAction(BreedingAction.Search(""))
            expanded = true
        }, modifier = Modifier.weight(1f)) { Text(name) }
        if (pokemonId > 0) BreedingPokemonSprite(pokemonId, name, onPreview)
    }
    if (expanded) {
        PokemonSelectionDialog(
            choices = if (first) state.choices else state.partnerChoices,
            query = state.query,
            onQuery = { onAction(BreedingAction.Search(it)) },
            onClose = { expanded = false },
            onSelect = {
                expanded = false
                onAction(BreedingAction.Species(first, it))
            }
        )
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
