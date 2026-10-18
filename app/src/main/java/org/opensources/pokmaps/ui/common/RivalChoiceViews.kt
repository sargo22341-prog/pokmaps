package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
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
                TeamVariantKind.PLAYER_STARTER -> StarterPicker(selection.variants, selected) {
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

@Composable
private fun StarterPicker(variants: List<TeamVariant>, selected: TeamVariant, onPick: (Int) -> Unit) {
    CompactSelect(selected, variants, { onPick(it.pokemonId) }) {
        stringResource(R.string.trainer_starter_option, it.pokemonName)
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
