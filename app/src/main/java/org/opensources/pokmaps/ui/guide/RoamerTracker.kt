package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.Roamers

@Composable
internal fun RoamerTracker(state: GuideUiState, onAction: (GuideAction) -> Unit) {
    Text(stringResource(R.string.guide_roamer_heading))
    val ids = if (state.library?.game?.versionId == 6) listOf(243, 244) else listOf(243, 244, 245)
    ids.forEach { id ->
        RoamerRow(id, state, onAction)
    }
}

@Composable
private fun RoamerRow(id: Int, state: GuideUiState, onAction: (GuideAction) -> Unit) {
    val observation = state.progress.roamers.firstOrNull { it.pokemonId == id }
    var expanded by rememberSaveable(id) { mutableStateOf(false) }
    Column {
        Text(
            stringResource(
                when (id) {
                    243 -> R.string.guide_raikou
                    244 -> R.string.guide_entei
                    245 -> R.string.guide_suicune
                    else -> error("Pokémon errant inconnu : $id")
                }
            )
        )
        Row {
            TextButton(onClick = { expanded = true }) {
                Text(
                    observation?.place?.let { stringResource(R.string.guide_route_number, it.removePrefix("route-")) }
                        ?: stringResource(R.string.guide_roamer_unknown)
                )
            }
            if (observation != null) {
                TextButton(onClick = { onAction(GuideAction.ShowPlace(observation.place)) }) {
                    Text(stringResource(R.string.show_on_map))
                }
            }
        }
        DropdownMenu(expanded, onDismissRequest = { expanded = false }) {
            DropdownMenuItem(text = { Text(stringResource(R.string.guide_roamer_clear)) }, onClick = {
                onAction(GuideAction.ObserveRoamer(id, null))
                expanded = false
            })
            Roamers.routes.forEach { route ->
                DropdownMenuItem(text = {
                    Text(stringResource(R.string.guide_route_number, route.toString()))
                }, onClick = {
                    onAction(GuideAction.ObserveRoamer(id, "route-$route"))
                    expanded = false
                })
            }
        }
    }
}
