package org.opensources.pokmaps.ui.pokemon

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect

/** Le chargement réussi d'une espèce absente ferme sa fiche ; une erreur reste consultable. */
@Composable
internal fun UnavailablePokemonEffect(state: PokemonUiState, onUnavailable: () -> Unit) {
    LaunchedEffect(state.loading, state.failed, state.game, state.details) {
        if (!state.loading && !state.failed && state.game != null && state.details == null) onUnavailable()
    }
}
