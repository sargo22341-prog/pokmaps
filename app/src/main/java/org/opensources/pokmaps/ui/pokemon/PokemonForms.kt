package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.pokemon.PokemonForm
import org.opensources.pokmaps.ui.common.CaughtButton
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@Composable
internal fun PokemonForms(
    forms: List<PokemonForm>,
    shiny: Boolean,
    caught: Set<String> = emptySet(),
    onToggle: ((String) -> Unit)? = null
) {
    if (forms.isEmpty()) return
    if (forms.size == 1 && onToggle == null) {
        Text(forms.single().name, style = MaterialTheme.typography.titleSmall)
        return
    }
    Text(stringResource(R.string.pokemon_forms_title), style = MaterialTheme.typography.bodySmall)
    if (forms.first().pokemonId == 351) {
        Text(stringResource(R.string.pokemon_forms_weather), style = MaterialTheme.typography.bodySmall)
    }
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        forms.forEach { form ->
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                val label = form.name
                PokemonSprite(
                    form.pokemonId,
                    SpritePlace.POKEMON_SHEET,
                    SpriteSize.LIST,
                    label,
                    modifier = Modifier.size(64.dp),
                    shiny = shiny,
                    form = form
                )
                Text(label, style = MaterialTheme.typography.labelSmall)
                if (onToggle != null) {
                    CaughtButton(
                        form.identifier in caught,
                        onToggle = { onToggle(form.identifier) }
                    )
                }
            }
        }
    }
}
