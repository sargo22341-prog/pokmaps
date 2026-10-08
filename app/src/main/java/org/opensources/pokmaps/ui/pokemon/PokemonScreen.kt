package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.PrimaryTabRow
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
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.ui.common.TypeBadge
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
    var movesTab by rememberSaveable(details.id, game.versionGroupId) { mutableIntStateOf(0) }
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
                (if (game.generationId >= 2) MOVE_TABS else MOVE_TABS.take(2)).forEachIndexed { index, label ->
                    Tab(
                        selected = movesTab == index,
                        onClick = { movesTab = index },
                        text = { Text(stringResource(label)) }
                    )
                }
            }
        }
        moves(
            when (movesTab) {
                0 -> details.levelUpMoves
                1 -> details.machineMoves
                2 -> details.eggMoves
                3 -> details.tutorMoves
                else -> error("Onglet inconnu : $movesTab")
            },
            links
        )
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

private val MOVE_TABS = listOf(
    R.string.pokemon_moves_level,
    R.string.pokemon_moves_machine,
    R.string.pokemon_moves_egg,
    R.string.pokemon_moves_tutor
)
