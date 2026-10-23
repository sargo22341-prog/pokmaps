package org.opensources.pokmaps.ui.guide

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R

@Composable
internal fun HgssBreedingResult(state: BreedingUiState) {
    if (state.natureParents.isEmpty()) {
        Text(stringResource(R.string.breeding_random_nature))
    } else {
        Text(stringResource(R.string.breeding_hgss_nature, state.natureParents.joinToString { (it + 1).toString() }))
    }
    state.forcedIvs.forEach { forced ->
        Text(
            stringResource(
                R.string.breeding_hgss_forced_iv,
                forced.parent + 1,
                stringResource(forced.stat.label()),
                forced.value?.toString() ?: stringResource(R.string.breeding_unknown_iv)
            )
        )
    }
}
