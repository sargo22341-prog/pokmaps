package org.opensources.pokmaps.ui.game

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game

@Composable
fun GameRoute(modifier: Modifier = Modifier, viewModel: GameViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    GameScreen(state, viewModel::onAction, modifier)
}

/** Choix du jeu : une rangée de jaquettes par génération. */
@Composable
fun GameScreen(state: GameUiState, onAction: (GameAction) -> Unit, modifier: Modifier = Modifier) {
    when {
        state.loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }

        state.failed || state.games.isEmpty() -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(stringResource(if (state.failed) R.string.data_load_error else R.string.games_empty))
        }

        else -> LazyColumn(modifier.fillMaxSize()) {
            item(key = "intro") {
                Text(
                    stringResource(R.string.game_intro),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(16.dp)
                )
            }
            state.byGeneration.forEach { (generation, games) -> generation(generation, games, state, onAction) }
        }
    }
}

private fun LazyListScope.generation(
    generation: Int,
    games: List<Game>,
    state: GameUiState,
    onAction: (GameAction) -> Unit
) {
    item(key = "generation-$generation") {
        Text(
            stringResource(R.string.game_generation, generation),
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 4.dp)
        )
    }
    item(key = "games-$generation") {
        LazyRow {
            items(games, key = { it.versionId }) { game ->
                GameRow(game, selected = game == state.selected, onSelect = { onAction(GameAction.Select(game)) })
            }
        }
    }
}

@Composable
private fun GameRow(game: Game, selected: Boolean, onSelect: () -> Unit) {
    Surface(
        color = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
        shape = MaterialTheme.shapes.medium,
        modifier = Modifier
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .selectable(selected = selected, role = Role.RadioButton, onClick = onSelect)
    ) {
        Box(Modifier.padding(8.dp)) {
            GameCover(game)
            if (selected) {
                Icon(
                    painterResource(R.drawable.ic_check),
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.align(Alignment.TopEnd)
                )
            }
        }
    }
}
