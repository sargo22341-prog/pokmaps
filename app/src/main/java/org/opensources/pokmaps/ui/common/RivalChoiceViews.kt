package org.opensources.pokmaps.ui.common

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.map.TeamSelection
import org.opensources.pokmaps.domain.map.TeamVariant
import org.opensources.pokmaps.domain.map.TeamVariantKind
import org.opensources.pokmaps.domain.model.SpritePlace

// Choix de la partie qui fixe l'équipe d'un rival : Pokémon de départ du joueur, ou combats de Jaune.

/** Encadré qui change l'équipe montrée ; rien pour un dresseur à équipe unique. */
@Composable
internal fun RivalChoicePanel(
    selection: TeamSelection,
    place: SpritePlace,
    failed: Boolean,
    onChoose: (RivalChoice) -> Unit
) {
    val selected = selection.selected ?: return
    Surface(
        color = MaterialTheme.colorScheme.surfaceContainerHigh,
        shape = MaterialTheme.shapes.large,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            when (selected.kind) {
                TeamVariantKind.PLAYER_STARTER -> StarterPicker(selection.variants, selected, place) {
                    onChoose(selection.choice.copy(starterId = it))
                }

                TeamVariantKind.RIVAL_EVOLUTION -> BattleOutcomes(selection.choice, selected, place, onChoose)
            }
            if (failed) {
                Text(
                    stringResource(R.string.rival_choice_write_error),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

/** Pokémon de départ côte à côte : celui choisi en grand sur une pastille, les autres réduits. */
@Composable
private fun StarterPicker(
    variants: List<TeamVariant>,
    selected: TeamVariant,
    place: SpritePlace,
    onPick: (Int) -> Unit
) {
    PanelTitle(stringResource(R.string.rival_choice_starter))
    Row(
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.Bottom,
        modifier = Modifier
            .fillMaxWidth()
            .selectableGroup()
    ) {
        variants.forEach { variant ->
            StarterOption(variant, variant == selected, place, Modifier.weight(1f)) { onPick(variant.pokemonId) }
        }
    }
}

@Composable
private fun StarterOption(
    variant: TeamVariant,
    selected: Boolean,
    place: SpritePlace,
    modifier: Modifier,
    onClick: () -> Unit
) {
    val scale by animateFloatAsState(if (selected) 1f else UNSELECTED_SCALE, label = "starterScale")
    val halo by animateColorAsState(
        if (selected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent,
        label = "starterHalo"
    )
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .clip(MaterialTheme.shapes.medium)
            .selectable(selected = selected, role = Role.RadioButton, onClick = onClick)
            .padding(vertical = 4.dp)
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    alpha = if (selected) 1f else UNSELECTED_ALPHA
                }
                .clip(CircleShape)
                .background(halo)
        ) {
            PokemonSprite(variant.pokemonId, place, SpriteSize.LIST, contentDescription = null)
        }
        Text(
            variant.pokemonName,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
            color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
    }
}

/** Jaune : issue des deux premiers combats, et l'évolution de l'Évoli du rival qui en découle. */
@Composable
private fun BattleOutcomes(
    choice: RivalChoice,
    selected: TeamVariant,
    place: SpritePlace,
    onChoose: (RivalChoice) -> Unit
) {
    PanelTitle(stringResource(R.string.rival_choice_battles))
    OutcomeSwitch(stringResource(R.string.rival_choice_lab_won), choice.wonLabBattle, enabled = true) {
        onChoose(choice.copy(wonLabBattle = it))
    }
    OutcomeSwitch(stringResource(R.string.rival_choice_route22_won), choice.wonRoute22Battle, choice.wonLabBattle) {
        onChoose(choice.copy(wonRoute22Battle = it))
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        PokemonSprite(selected.pokemonId, place, SpriteSize.SMALL, contentDescription = null)
        Text(
            stringResource(R.string.rival_choice_evolution, selected.pokemonName),
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun OutcomeSwitch(label: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clip(MaterialTheme.shapes.medium)
            .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange)
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.outline,
            modifier = Modifier.weight(1f)
        )
        Switch(checked = checked, onCheckedChange = null, enabled = enabled)
    }
}

@Composable
private fun PanelTitle(text: String) {
    Text(text, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

private const val UNSELECTED_SCALE = 0.65f
private const val UNSELECTED_ALPHA = 0.6f
