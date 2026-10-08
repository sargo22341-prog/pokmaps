package org.opensources.pokmaps.ui.settings

import androidx.annotation.StringRes
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.LocalAnimatedPlaces
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@Composable
fun SettingsRoute(onOpenAbout: () -> Unit, viewModel: SettingsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    SettingsScreen(state, viewModel::onAction, onOpenAbout) {
        CollectionBackupRoute()
        HorizontalDivider(Modifier.padding(vertical = 8.dp))
        RetroSettingsRoute()
    }
}

/** Réglages : sprites animés (partout, ou endroit par endroit), captures comptées, et écran « À propos ». */
@Composable
fun SettingsScreen(
    state: SettingsUiState,
    onAction: (SettingsAction) -> Unit,
    onOpenAbout: () -> Unit,
    content: @Composable () -> Unit = {}
) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        if (state.failed) {
            Text(
                stringResource(R.string.data_load_error),
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(16.dp)
            )
        }
        SettingsTitle(stringResource(R.string.settings_display))
        AnimatedSpritesSetting(state, onAction)
        HorizontalDivider(Modifier.padding(vertical = 8.dp))
        SettingsTitle(stringResource(R.string.settings_collection))
        CaptureScopeSetting(state.captureScope) { onAction(SettingsAction.SetCaptureScope(it)) }
        HorizontalDivider(Modifier.padding(vertical = 8.dp))
        content()
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

@Composable
private fun SettingsTitle(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 8.dp)
    )
}

/**
 * Interrupteur général des sprites animés (partout ou nulle part), et sous-menu dépliable pour choisir endroit par
 * endroit : carte, liste du lieu, Pokédex, fiche Pokémon, évolutions, fiches, recherche.
 */
@Composable
private fun AnimatedSpritesSetting(state: SettingsUiState, onAction: (SettingsAction) -> Unit) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    val summary = when {
        state.allAnimated -> stringResource(R.string.settings_animated_everywhere)

        state.partlyAnimated -> pluralStringResource(
            R.plurals.settings_animated_some,
            state.animatedPlaces.size,
            state.animatedPlaces.size,
            SpritePlace.entries.size
        )

        else -> stringResource(R.string.settings_animated_nowhere)
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        SwitchRow(
            title = stringResource(R.string.settings_animated_sprites),
            summary = summary,
            checked = state.allAnimated,
            onCheckedChange = { onAction(SettingsAction.SetAllAnimated(it)) },
            modifier = Modifier.weight(1f)
        )
        IconButton(onClick = { expanded = !expanded }, modifier = Modifier.padding(end = 8.dp)) {
            Icon(
                painterResource(R.drawable.ic_arrow_down),
                contentDescription = stringResource(
                    if (expanded) R.string.settings_animated_collapse else R.string.settings_animated_expand
                ),
                modifier = Modifier.rotate(if (expanded) HALF_TURN else 0f)
            )
        }
    }
    AnimatedVisibility(expanded) {
        Column(Modifier.padding(start = 24.dp)) {
            SpritePlace.entries.forEach { place ->
                SwitchRow(
                    title = stringResource(place.title),
                    summary = stringResource(place.summary),
                    checked = place in state.animatedPlaces,
                    onCheckedChange = { onAction(SettingsAction.SetAnimated(place, it)) }
                )
            }
        }
    }
    if (state.animatedPlaces.isNotEmpty()) {
        // Aperçu : Pikachu animé.
        CompositionLocalProvider(LocalAnimatedPlaces provides setOf(SpritePlace.POKEMON_SHEET)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                PokemonSprite(PREVIEW_POKEMON, SpritePlace.POKEMON_SHEET, SpriteSize.LIST, contentDescription = null)
            }
        }
    }
}

/** Réglage activable : titre, explication et interrupteur (toute la ligne se touche). */
@Composable
private fun SwitchRow(
    title: String,
    summary: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        modifier = modifier
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

@get:StringRes
private val SpritePlace.title: Int
    get() = when (this) {
        SpritePlace.MAP -> R.string.nav_map
        SpritePlace.MAP_LIST -> R.string.sprite_place_map_list
        SpritePlace.POKEDEX -> R.string.nav_pokedex
        SpritePlace.POKEMON_SHEET -> R.string.pokemon_title
        SpritePlace.EVOLUTIONS -> R.string.sprite_place_evolutions
        SpritePlace.SHEETS -> R.string.sprite_place_sheets
        SpritePlace.SEARCH -> R.string.search_title
    }

@get:StringRes
private val SpritePlace.summary: Int
    get() = when (this) {
        SpritePlace.MAP -> R.string.sprite_place_map_summary
        SpritePlace.MAP_LIST -> R.string.sprite_place_map_list_summary
        SpritePlace.POKEDEX -> R.string.sprite_place_pokedex_summary
        SpritePlace.POKEMON_SHEET -> R.string.sprite_place_pokemon_sheet_summary
        SpritePlace.EVOLUTIONS -> R.string.sprite_place_evolutions_summary
        SpritePlace.SHEETS -> R.string.sprite_place_sheets_summary
        SpritePlace.SEARCH -> R.string.sprite_place_search_summary
    }

private const val PREVIEW_POKEMON = 25
private const val HALF_TURN = 180f
