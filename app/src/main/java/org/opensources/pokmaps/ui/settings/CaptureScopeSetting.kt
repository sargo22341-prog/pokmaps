package org.opensources.pokmaps.ui.settings

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.pokedex.CaptureScope

/**
 * Curseur à trois positions : un Pokémon capturé compte pour le jeu choisi, pour toute sa génération, ou pour tous
 * les jeux. Les captures restent mémorisées jeu par jeu, quel que soit le réglage.
 */
@Composable
internal fun CaptureScopeSetting(scope: CaptureScope, onChange: (CaptureScope) -> Unit) {
    val scopes = CaptureScope.entries
    val label = stringResource(scope.label)
    Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
        Text(stringResource(R.string.settings_capture_scope), style = MaterialTheme.typography.bodyLarge)
        Text(
            stringResource(scope.summary),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Slider(
            value = scopes.indexOf(scope).toFloat(),
            onValueChange = { value ->
                val chosen = scopes[value.roundToInt().coerceIn(scopes.indices)]
                if (chosen != scope) onChange(chosen)
            },
            valueRange = 0f..scopes.lastIndex.toFloat(),
            // Positions intermédiaires entre la première et la dernière.
            steps = scopes.size - 2,
            modifier = Modifier.semantics { stateDescription = label }
        )
        Row(Modifier.fillMaxWidth()) {
            scopes.forEach { position ->
                Text(
                    stringResource(position.label),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = if (position == scope) FontWeight.Bold else FontWeight.Normal,
                    color = if (position == scope) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                    textAlign = when (position) {
                        scopes.first() -> TextAlign.Start
                        scopes.last() -> TextAlign.End
                        else -> TextAlign.Center
                    },
                    modifier = Modifier.weight(1f)
                )
            }
        }
        Text(
            stringResource(R.string.settings_capture_scope_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 8.dp)
        )
    }
}

@get:StringRes
private val CaptureScope.label: Int
    get() = when (this) {
        CaptureScope.GAME -> R.string.nav_game
        CaptureScope.GENERATION -> R.string.settings_capture_scope_generation
        CaptureScope.ALL -> R.string.settings_capture_scope_all
    }

@get:StringRes
private val CaptureScope.summary: Int
    get() = when (this) {
        CaptureScope.GAME -> R.string.settings_capture_scope_game_summary
        CaptureScope.GENERATION -> R.string.settings_capture_scope_generation_summary
        CaptureScope.ALL -> R.string.settings_capture_scope_all_summary
    }
