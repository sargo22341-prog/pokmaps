package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.formatNumber
import org.opensources.pokmaps.ui.common.label

/** Fiches ouvertes depuis la fiche d'un Pokémon : autre Pokémon, objet (pierre, CT / CS) ou attaque. */
data class PokemonLinks(
    val onOpenPokemon: (Int) -> Unit,
    val onOpenItem: (String) -> Unit,
    val onOpenMove: (Int) -> Unit
)

@Composable
fun PokemonRoute(
    links: PokemonLinks,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PokemonViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    PokemonScreen(
        state,
        onAction = { action ->
            viewModel.onAction(action)
            if (action == PokemonAction.ShowOnMap) onShowOnMap()
        },
        links = links,
        modifier = modifier
    )
}

@Composable
fun PokemonScreen(
    state: PokemonUiState,
    onAction: (PokemonAction) -> Unit,
    links: PokemonLinks,
    modifier: Modifier = Modifier
) {
    val details = state.details
    val game = state.game
    when {
        state.loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }

        details == null || game == null -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(stringResource(if (state.failed) R.string.data_load_error else R.string.pokemon_not_found))
        }

        else -> PokemonContent(state, game, details, onAction, links, modifier)
    }
}

@Composable
private fun PokemonContent(
    state: PokemonUiState,
    game: Game,
    details: PokemonDetails,
    onAction: (PokemonAction) -> Unit,
    links: PokemonLinks,
    modifier: Modifier = Modifier
) {
    var movesTab by rememberSaveable(details.id) { mutableIntStateOf(0) }
    LazyColumn(modifier.fillMaxSize()) {
        item { PokemonHeader(state, game, details, onAction) }
        section(R.string.pokemon_stats) { Stats(details.stats) }
        if (state.has(GenerationFeature.ABILITIES)) section(R.string.pokemon_abilities) { Abilities(details.traits) }
        section(R.string.pokemon_weaknesses) { Weaknesses(details) }
        section(R.string.pokemon_evolutions) {
            Evolutions(details, state.shiny, links.onOpenPokemon, links.onOpenItem)
        }
        section(R.string.pokemon_locations) { Locations(game, details) { onAction(PokemonAction.ShowOnMap) } }
        if (state.has(GenerationFeature.HELD_ITEMS)) {
            section(R.string.pokemon_held_items) { HeldItems(game, details.traits, links.onOpenItem) }
        }
        state.shinyOdds?.let { odds -> section(R.string.pokemon_shiny) { ShinyOddsText(odds, game) } }
        if (state.has(GenerationFeature.GENDER)) section(R.string.pokemon_gender) { Gender(details.traits) }
        if (state.has(GenerationFeature.BREEDING)) section(R.string.pokemon_breeding) { Breeding(details.traits) }
        state.catch?.let { section(R.string.catch_title) { CatchCalculator(it, onAction) } }
        section(R.string.pokemon_moves) {
            PrimaryTabRow(selectedTabIndex = movesTab) {
                MOVE_TABS.forEachIndexed { index, label ->
                    Tab(
                        selected = movesTab == index,
                        onClick = { movesTab = index },
                        text = { Text(stringResource(label)) }
                    )
                }
            }
        }
        moves(if (movesTab == 0) details.levelUpMoves else details.machineMoves, links)
        item { Box(Modifier.height(24.dp)) }
    }
}

private fun LazyListScope.section(title: Int, content: @Composable () -> Unit) {
    item(key = title) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            HorizontalDivider(Modifier.padding(bottom = 12.dp))
            Text(
                stringResource(title),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            content()
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CatchCalculator(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.catch_level, catch.level), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = catch.level.toFloat(),
            onValueChange = { onAction(PokemonAction.SetCatchLevel(it.toInt())) },
            valueRange = 1f..PokemonViewModel.MAX_LEVEL.toFloat()
        )
        Text(stringResource(R.string.catch_hp), style = MaterialTheme.typography.bodyMedium)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            HpChoice.entries.forEach { hp ->
                FilterChip(selected = catch.hp == hp, onClick = {
                    onAction(PokemonAction.SetCatchHp(hp))
                }, label = { Text(stringResource(hp.label)) })
            }
        }
        Text(stringResource(R.string.status_label), style = MaterialTheme.typography.bodyMedium)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CatchStatus.entries.forEach { status ->
                FilterChip(
                    selected = catch.status == status,
                    onClick = { onAction(PokemonAction.SetCatchStatus(status)) },
                    label = { Text(stringResource(status.label)) }
                )
            }
        }
        catch.probabilities.forEach { (ball, probability) ->
            val best = ball == catch.best
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PixelArtImage(Sprites.item(ball.itemIdentifier), PixelArt.ITEM_ICON, 64.dp, contentDescription = null)
                Column(Modifier.weight(1f)) {
                    Text(stringResource(ball.label), fontWeight = if (best) FontWeight.Bold else FontWeight.Normal)
                    if (best) {
                        Text(
                            stringResource(R.string.catch_best),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
                Text(
                    stringResource(R.string.encounter_chance, formatNumber(probability * PERCENT)),
                    fontWeight = if (best) FontWeight.Bold else FontWeight.Normal
                )
            }
        }
        Text(
            stringResource(R.string.catch_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

private fun LazyListScope.moves(moves: List<LearnedMove>, links: PokemonLinks) {
    if (moves.isEmpty()) {
        item { Text(stringResource(R.string.pokemon_moves_none), modifier = Modifier.padding(16.dp)) }
        return
    }
    items(moves, key = { "${it.machine?.identifier ?: it.level}-${it.moveId}" }) { move ->
        // Une CT / CS ouvre sa fiche, qui dit ce que fait l'attaque ; une attaque apprise par niveau ouvre la sienne.
        val machine = move.machine
        if (machine != null) {
            MoveRow(move, stringResource(R.string.move_open_machine, machine.name)) {
                links.onOpenItem(machine.identifier)
            }
        } else {
            MoveRow(move, stringResource(R.string.move_open)) { links.onOpenMove(move.moveId) }
        }
    }
}

@Composable
private fun MoveRow(move: LearnedMove, clickLabel: String, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clickable(onClickLabel = clickLabel, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 6.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                move.machine?.name
                    ?: if (move.level <= 1) {
                        stringResource(R.string.move_start)
                    } else {
                        stringResource(R.string.encounter_levels, move.level)
                    },
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.width(56.dp)
            )
            Text(move.name, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
            TypeBadge(move.type)
        }
        val none = stringResource(R.string.no_value)
        Text(
            listOf(
                stringResource(move.damageClass.label),
                "${stringResource(R.string.move_power)} ${move.power ?: none}",
                "${stringResource(R.string.move_accuracy)} ${move.accuracy?.let { "$it %" } ?: none}",
                "${stringResource(R.string.move_pp)} ${move.pp}"
            ).joinToString(" · "),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 64.dp)
        )
    }
}

private val HpChoice.label: Int
    get() = when (this) {
        HpChoice.FULL -> R.string.catch_hp_full
        HpChoice.HALF -> R.string.catch_hp_half
        HpChoice.QUARTER -> R.string.catch_hp_quarter
        HpChoice.ONE -> R.string.catch_hp_one
    }

private val CatchStatus.label: Int
    get() = when (this) {
        CatchStatus.NONE -> R.string.catch_status_none
        CatchStatus.SLEEP_OR_FREEZE -> R.string.catch_status_sleep
        CatchStatus.PARALYSIS_BURN_OR_POISON -> R.string.catch_status_paralysis
    }

private val Ball.label: Int
    get() = when (this) {
        Ball.POKE -> R.string.ball_poke
        Ball.GREAT -> R.string.ball_great
        Ball.ULTRA -> R.string.ball_ultra
        Ball.SAFARI -> R.string.ball_safari
        Ball.MASTER -> R.string.ball_master
    }

private val MOVE_TABS = listOf(R.string.pokemon_moves_level, R.string.pokemon_moves_machine)
private const val PERCENT = 100
