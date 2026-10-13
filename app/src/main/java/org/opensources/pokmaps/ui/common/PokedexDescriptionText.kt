package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.pokemon.PokedexDescription

/** Description du Pokédex, suivie du jeu d'où elle vient : ce n'est pas forcément le jeu choisi. */
@Composable
fun PokedexDescriptionText(description: PokedexDescription, modifier: Modifier = Modifier) {
    Column(modifier) {
        Text(description.text, style = MaterialTheme.typography.bodyMedium)
        Text(
            stringResource(R.string.pokemon_description_source, description.versionName),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
