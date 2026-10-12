package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.RoamerChoice
import org.opensources.pokmaps.domain.guide.RoamerCondition
import org.opensources.pokmaps.domain.guide.RoamerLocation

@Composable
internal fun RoamerTool(state: GuideUiState, onAction: (GuideAction) -> Unit) {
    var expanded by remember(state.library?.game?.versionId) { mutableStateOf(false) }
    Card {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { expanded = !expanded }) {
                Text(stringResource(R.string.guide_roamers_title))
            }
            if (expanded) {
                Text(stringResource(R.string.guide_roamers_hint), style = MaterialTheme.typography.bodySmall)
                state.roamers.forEach { choice -> RoamerRow(choice, state, onAction) }
            }
        }
    }
}

@Composable
private fun RoamerRow(choice: RoamerChoice, state: GuideUiState, onAction: (GuideAction) -> Unit) {
    val observed = state.observedRoamers[choice.pokemonId]
    var selecting by remember(state.library?.game?.versionId, choice.pokemonId) { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(stringResource(pokemonLabel(choice.pokemonId)), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(choice.condition.label()), style = MaterialTheme.typography.bodySmall)
        OutlinedButton(onClick = { selecting = true }) {
            val name = observed?.let { locationName(it) } ?: stringResource(R.string.guide_roamer_unknown)
            Text(stringResource(R.string.guide_roamer_position, name))
        }
        DropdownMenu(selecting, onDismissRequest = { selecting = false }) {
            state.roamerLocations.forEach { location ->
                DropdownMenuItem(text = { Text(locationName(location)) }, onClick = {
                    selecting = false
                    onAction(GuideAction.ObserveRoamer(choice.pokemonId, location.identifier))
                })
            }
        }
        if (observed != null) {
            TextButton(onClick = { onAction(GuideAction.ShowPlace(observed.identifier)) }) {
                Text(stringResource(R.string.guide_roamer_map))
            }
            TextButton(onClick = { onAction(GuideAction.ObserveRoamer(choice.pokemonId, null)) }) {
                Text(stringResource(R.string.guide_roamer_forget))
            }
        }
    }
}

@Composable
private fun locationName(location: RoamerLocation): String = stringResource(
    when {
        location.north -> R.string.guide_roamer_north
        location.water -> R.string.guide_roamer_water
        else -> R.string.guide_roamer_route
    },
    location.number
)

private fun pokemonLabel(pokemon: Int): Int = when (pokemon) {
    243 -> R.string.guide_roamer_raikou
    244 -> R.string.guide_roamer_entei
    245 -> R.string.guide_roamer_suicune
    380 -> R.string.guide_roamer_latias
    381 -> R.string.guide_roamer_latios
    else -> error("Pokémon errant inconnu : $pokemon")
}

private fun RoamerCondition.label(): Int = when (this) {
    RoamerCondition.JOHTO -> R.string.guide_roamer_johto
    RoamerCondition.HOENN -> R.string.guide_roamer_hoenn
    RoamerCondition.RED -> R.string.guide_roamer_red
    RoamerCondition.BLUE -> R.string.guide_roamer_blue
    RoamerCondition.BULBASAUR -> R.string.guide_roamer_bulbasaur
    RoamerCondition.CHARMANDER -> R.string.guide_roamer_charmander
    RoamerCondition.SQUIRTLE -> R.string.guide_roamer_squirtle
}
