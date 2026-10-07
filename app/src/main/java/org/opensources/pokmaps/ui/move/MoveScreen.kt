package org.opensources.pokmaps.ui.move

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.MoveDetails
import org.opensources.pokmaps.domain.pokemon.MoveLearner
import org.opensources.pokmaps.domain.usecase.MovePage
import org.opensources.pokmaps.ui.common.MoveEffectText
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SheetRow
import org.opensources.pokmaps.ui.common.SpriteSize
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.label

@Composable
fun MoveRoute(
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MoveViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    MoveScreen(state, onOpenPokemon, onOpenItem, modifier)
}

/** Fiche d'une attaque : caractéristiques, effet, CT / CS qui l'enseigne et Pokémon qui l'apprennent. */
@Composable
fun MoveScreen(
    state: MoveUiState,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val page = state.page
    val move = page?.details
    if (page == null || move == null) {
        SheetPlaceholder(state.loading, stringResource(R.string.move_not_found), modifier, state.failed)
        return
    }
    LazyColumn(modifier.fillMaxSize()) {
        item(key = "header") { MoveHeader(move) }
        section("effect", R.string.move_effect) { MoveEffectText(move.effect) }
        move.machine?.let { machine ->
            section("machine", R.string.move_machine) {
                SheetRow(
                    title = machine.name,
                    subtitle = stringResource(R.string.move_open_machine, machine.name),
                    onClick = { onOpenItem(machine.identifier) },
                    content = {
                        PixelArtImage(Sprites.item(machine.identifier), PixelArt.ITEM_ICON, 48.dp, null)
                    }
                )
            }
        }
        learners(page, move, onOpenPokemon)
        item(key = "end") { Box(Modifier.height(24.dp)) }
    }
}

/** Nom, type, catégorie, puissance, précision et PP. */
@Composable
private fun MoveHeader(move: MoveDetails) {
    val none = stringResource(R.string.no_value)
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        Text(move.name, style = MaterialTheme.typography.headlineMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            TypeBadge(move.type)
            Text(stringResource(move.damageClass.label), style = MaterialTheme.typography.titleSmall)
        }
        Row(horizontalArrangement = Arrangement.SpaceEvenly, modifier = Modifier.fillMaxWidth()) {
            MoveStat(stringResource(R.string.move_power_full), move.power?.toString() ?: none)
            MoveStat(
                stringResource(R.string.move_accuracy_full),
                move.accuracy?.let { stringResource(R.string.encounter_chance, it.toString()) } ?: none
            )
            MoveStat(stringResource(R.string.move_pp), move.pp.toString())
        }
    }
}

@Composable
private fun MoveStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Pokémon qui l'apprennent en montant de niveau, puis avec la CT / CS ; vers leur fiche. */
private fun LazyListScope.learners(page: MovePage, move: MoveDetails, onOpenPokemon: (Int) -> Unit) {
    if (move.learners.isEmpty()) {
        section("learners", R.string.move_learners) {
            Text(stringResource(R.string.move_learners_none, page.game.name))
        }
        return
    }
    if (move.levelUpLearners.isNotEmpty()) {
        item(key = "level-up-learners") { SectionTitle(stringResource(R.string.move_learners_level), TITLE_PADDING) }
        items(move.levelUpLearners, key = { "level-${it.pokemonId}-${it.level}" }) { learner ->
            LearnerRow(learner, onOpenPokemon)
        }
    }
    val machine = move.machine
    if (machine != null && move.machineLearners.isNotEmpty()) {
        item(key = "machine-learners") {
            SectionTitle(stringResource(R.string.move_learners_machine, machine.name), TITLE_PADDING)
        }
        items(move.machineLearners, key = { "machine-${it.pokemonId}" }) { learner ->
            LearnerRow(learner, onOpenPokemon)
        }
    }
}

@Composable
private fun LearnerRow(learner: MoveLearner, onOpenPokemon: (Int) -> Unit) {
    val level = learner.level
    SheetRow(
        title = learner.name,
        trailing = when {
            level == null -> null
            level <= 1 -> stringResource(R.string.move_start)
            else -> stringResource(R.string.encounter_levels, level)
        },
        onClick = { onOpenPokemon(learner.pokemonId) },
        modifier = Modifier.padding(horizontal = 16.dp),
        content = {
            PokemonSprite(learner.pokemonId, SpritePlace.SHEETS, SpriteSize.LIST, contentDescription = null)
        }
    )
}

private fun LazyListScope.section(key: String, title: Int, content: @Composable () -> Unit) {
    item(key = key) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            SectionTitle(stringResource(title))
            content()
        }
    }
}

@Composable
private fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Column(modifier) {
        HorizontalDivider(Modifier.padding(bottom = 12.dp))
        Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 8.dp))
    }
}

private val TITLE_PADDING = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
