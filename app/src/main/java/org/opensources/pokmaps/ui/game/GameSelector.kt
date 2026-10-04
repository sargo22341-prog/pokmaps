package org.opensources.pokmaps.ui.game

import androidx.compose.foundation.layout.Box
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game

/** Bouton « Pokémon Rouge ▾ » ouvrant la liste des jeux. */
@Composable
fun GameSelector(state: GameUiState, onSelect: (Game) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val selected = state.selected ?: return
    Box {
        TextButton(onClick = { expanded = true }) {
            Text(stringResource(R.string.game_selector, selected.name))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            state.games.forEach { game ->
                DropdownMenuItem(
                    text = { Text(stringResource(R.string.game_name, game.name)) },
                    onClick = {
                        expanded = false
                        onSelect(game)
                    }
                )
            }
        }
    }
}
