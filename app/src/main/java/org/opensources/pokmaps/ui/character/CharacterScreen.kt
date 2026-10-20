package org.opensources.pokmaps.ui.character

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.TrainerTeam
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.usecase.CharacterPage
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.Offers
import org.opensources.pokmaps.ui.common.RoleIcons
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.TrainerPartyBalls
import org.opensources.pokmaps.ui.common.TrainerTeams

@Composable
fun CharacterRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: CharacterViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    CharacterScreen(
        state,
        onAction = { action ->
            viewModel.onAction(action)
            when (action) {
                CharacterAction.ShowOnMap, is CharacterAction.ShowObject -> onShowOnMap()
                is CharacterAction.ChooseRival -> Unit
            }
        },
        onOpenPokemon = onOpenPokemon,
        onOpenItem = onOpenItem,
        onOpenPlace = onOpenPlace,
        modifier = modifier
    )
}

@Composable
fun CharacterScreen(
    state: CharacterUiState,
    onAction: (CharacterAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.character_not_found), modifier, state.failed)
        return
    }
    CharacterContent(
        state,
        page,
        onAction = onAction,
        onOpenPokemon = onOpenPokemon,
        onOpenItem = onOpenItem,
        onOpenPlace = onOpenPlace,
        modifier = modifier
    )
}

@Composable
private fun CharacterContent(
    state: CharacterUiState,
    page: CharacterPage,
    onAction: (CharacterAction) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val obj = page.obj
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        if (obj.kind == MapObjectKind.TRAINER) {
            TrainerTeams(
                state.teams,
                SpritePlace.SHEETS,
                state.choiceFailed,
                onChooseRival = { onAction(CharacterAction.ChooseRival(it)) },
                onOpenPokemon = onOpenPokemon,
                header = { teams -> CharacterHeader(page, teams, onAction, onOpenPlace) }
            )
        } else {
            CharacterHeader(page, emptyList(), onAction, onOpenPlace)
        }
        Offers(
            page.offers,
            SpritePlace.SHEETS,
            page.fossilUses,
            onOpenPokemon = onOpenPokemon,
            onOpenItem = onOpenItem,
            onShowObject = { onAction(CharacterAction.ShowObject(it)) }
        )
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun CharacterHeader(
    page: CharacterPage,
    teams: List<TrainerTeam>,
    onAction: (CharacterAction) -> Unit,
    onOpenPlace: (String) -> Unit
) {
    Box(Modifier.fillMaxWidth()) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            CharacterSprite(page.obj, page.game.versionGroupIdentifier, size = 96)
            RoleIcons(page.roles.filter { it != CharacterRole.BATTLE }, size = 28.dp)
            Text(page.obj.name, style = MaterialTheme.typography.headlineMedium)
            FilledTonalButton(onClick = { onOpenPlace(page.map.identifier) }) { Text(page.map.name) }
            Button(onClick = { onAction(CharacterAction.ShowOnMap) }) {
                Icon(
                    painterResource(R.drawable.ic_map),
                    contentDescription = null,
                    modifier = Modifier.padding(end = 8.dp)
                )
                Text(stringResource(R.string.show_on_map))
            }
        }
        Column(Modifier.align(Alignment.TopEnd)) { teams.forEach { TrainerPartyBalls(it) } }
    }
}
