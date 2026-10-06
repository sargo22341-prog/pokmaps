package org.opensources.pokmaps.ui.character

import androidx.compose.foundation.layout.Arrangement
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
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.usecase.CharacterPage
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.map.CharacterSprite
import org.opensources.pokmaps.ui.map.Offers
import org.opensources.pokmaps.ui.map.SectionTitle
import org.opensources.pokmaps.ui.map.TrainerPokemonRow
import org.opensources.pokmaps.ui.map.displayName

@Composable
fun CharacterScreen(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: CharacterViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val page = state.page
    if (page == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.character_not_found), modifier, state.failed)
        return
    }
    CharacterContent(
        page,
        onOpenPokemon = onOpenPokemon,
        onOpenItem = onOpenItem,
        onOpenPlace = onOpenPlace,
        onShowOnMap = {
            viewModel.showOnMap()
            onShowOnMap()
        },
        modifier = modifier
    )
}

@Composable
private fun CharacterContent(
    page: CharacterPage,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onOpenPlace: (String) -> Unit,
    onShowOnMap: () -> Unit,
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
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            CharacterSprite(obj, page.game.versionGroupIdentifier, size = 96)
            if (obj.kind == MapObjectKind.TRAINER) {
                Text(stringResource(R.string.map_trainer), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(obj.displayName(), style = MaterialTheme.typography.headlineMedium)
            FilledTonalButton(onClick = { onOpenPlace(page.map.identifier) }) { Text(page.map.name) }
            Button(onClick = onShowOnMap) {
                Icon(
                    painterResource(R.drawable.ic_map),
                    contentDescription = null,
                    modifier = Modifier.padding(end = 8.dp)
                )
                Text(stringResource(R.string.sheet_show_on_map))
            }
        }
        if (obj.kind == MapObjectKind.TRAINER) {
            if (page.party.isEmpty()) {
                Text(stringResource(R.string.map_trainer_starter), style = MaterialTheme.typography.bodyMedium)
            } else {
                SectionTitle(stringResource(R.string.map_trainer_party))
                page.party.forEach { TrainerPokemonRow(it, onOpenPokemon) }
            }
        }
        Offers(page.offers, onOpenPokemon = onOpenPokemon, onOpenItem = onOpenItem)
        Spacer(Modifier.height(24.dp))
    }
}
