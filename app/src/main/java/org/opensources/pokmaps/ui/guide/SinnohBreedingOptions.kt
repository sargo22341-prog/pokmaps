package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R

@Composable
internal fun SinnohLanguage(state: BreedingUiState, onAction: (BreedingAction) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(state.first.foreignLanguage, {
            onAction(BreedingAction.Values(true, state.first.copy(foreignLanguage = it)))
        })
        Text(stringResource(R.string.breeding_different_languages))
    }
}
