package org.opensources.pokmaps.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.ui.common.AnimatedPokemonSprite

/** Réglages : sprites animés (Pokédex et fiches, carte), et accès à l'écran « À propos ». */
@Composable
fun SettingsScreen(onOpenAbout: () -> Unit, viewModel: SettingsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        Text(
            stringResource(R.string.settings_display),
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 8.dp)
        )
        SwitchRow(
            title = stringResource(R.string.settings_animated_sprites),
            summary = stringResource(R.string.settings_animated_sprites_summary),
            checked = state.animatedSprites,
            onCheckedChange = viewModel::setAnimatedSprites
        )
        SwitchRow(
            title = stringResource(R.string.settings_map_animated_sprites),
            summary = stringResource(R.string.settings_map_animated_sprites_summary),
            checked = state.mapAnimatedSprites,
            onCheckedChange = viewModel::setMapAnimatedSprites
        )
        if (state.animatedSprites || state.mapAnimatedSprites) {
            // Aperçu : Pikachu animé.
            AnimatedPokemonSprite(
                PREVIEW_POKEMON,
                contentDescription = null,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .size(96.dp)
            )
        }
        HorizontalDivider(Modifier.padding(vertical = 8.dp))
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onOpenAbout)
                .padding(horizontal = 16.dp, vertical = 16.dp)
        ) {
            Icon(painterResource(R.drawable.ic_info), contentDescription = null)
            Text(stringResource(R.string.about_title), style = MaterialTheme.typography.bodyLarge)
        }
    }
}

/** Réglage activable : titre, explication et interrupteur (toute la ligne se touche). */
@Composable
private fun SwitchRow(title: String, summary: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        modifier = Modifier
            .fillMaxWidth()
            .toggleable(checked, role = Role.Switch, onValueChange = onCheckedChange)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(
                summary,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Switch(checked = checked, onCheckedChange = null)
    }
}

private const val PREVIEW_POKEMON = 25
