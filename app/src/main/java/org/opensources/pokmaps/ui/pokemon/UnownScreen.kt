package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.LocalAnimatedPlaces

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun UnownRoute(onDismiss: () -> Unit, shiny: Boolean, viewModel: UnownViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ModalBottomSheet(onDismissRequest = onDismiss) { UnownScreen(state, viewModel::toggle, shiny) }
}

@Composable
internal fun UnownScreen(state: UnownUiState, onToggle: (UnownForm) -> Unit, shiny: Boolean) {
    Column(Modifier.fillMaxWidth().padding(16.dp)) {
        Text(stringResource(R.string.unown_title), style = MaterialTheme.typography.titleLarge)
        if (state.failed) Text(stringResource(R.string.data_load_error), color = MaterialTheme.colorScheme.error)
        if (state.loading) CircularProgressIndicator()
        val collection = state.collection
        if (collection != null) {
            Text(stringResource(R.string.unown_progress, collection.caught.size, collection.forms.size))
            if (collection.forms.isEmpty()) Text(stringResource(R.string.unown_empty))
            LazyVerticalGrid(columns = GridCells.Adaptive(88.dp)) {
                items(collection.forms, key = { it.identifier }) { form ->
                    UnownCell(form, form in collection.caught, shiny) { onToggle(form) }
                }
            }
        }
    }
}

@Composable
private fun UnownCell(form: UnownForm, caught: Boolean, shiny: Boolean, onToggle: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.toggleable(value = caught, role = Role.Checkbox, onValueChange = { onToggle() })
    ) {
        val description = stringResource(R.string.unown_form, form.symbol)
        AssetImage(
            form.sprite(SpritePlace.POKEDEX in LocalAnimatedPlaces.current, shiny),
            contentDescription = description,
            modifier = Modifier.size(80.dp).padding(8.dp)
        )
        Text(description)
        Checkbox(checked = caught, onCheckedChange = null)
    }
}
