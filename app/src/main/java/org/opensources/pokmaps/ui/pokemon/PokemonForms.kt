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
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@Composable
internal fun PokemonForms(pokemonId: Int, version: String, shiny: Boolean) {
    val forms = PokemonForm.available(pokemonId, version)
    if (forms.isEmpty()) return
    if (forms.size == 1) {
        Text(stringResource(formLabel(forms.single())), style = MaterialTheme.typography.titleSmall)
        return
    }
    Text(stringResource(R.string.pokemon_forms_weather), style = MaterialTheme.typography.bodySmall)
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        forms.forEach { form ->
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                val label = stringResource(formLabel(form))
                PokemonSprite(
                    pokemonId,
                    SpritePlace.POKEMON_SHEET,
                    SpriteSize.LIST,
                    label,
                    modifier = Modifier.size(64.dp),
                    shiny = shiny,
                    form = form
                )
                Text(label, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

private fun formLabel(form: PokemonForm): Int = when (form) {
    PokemonForm.CASTFORM_NORMAL, PokemonForm.DEOXYS_NORMAL -> R.string.pokemon_form_normal
    PokemonForm.CASTFORM_SUNNY -> R.string.pokemon_form_sunny
    PokemonForm.CASTFORM_RAINY -> R.string.pokemon_form_rainy
    PokemonForm.CASTFORM_SNOWY -> R.string.pokemon_form_snowy
    PokemonForm.DEOXYS_ATTACK -> R.string.pokemon_form_attack
    PokemonForm.DEOXYS_DEFENSE -> R.string.pokemon_form_defense
    PokemonForm.DEOXYS_SPEED -> R.string.pokemon_form_speed
}
