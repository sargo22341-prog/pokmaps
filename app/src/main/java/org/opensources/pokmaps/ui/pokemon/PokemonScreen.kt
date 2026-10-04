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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil3.compose.AsyncImage
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.BaseStat
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionNode
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.formatFactor
import org.opensources.pokmaps.ui.common.formatNumber
import org.opensources.pokmaps.ui.common.label

@Composable
fun PokemonScreen(
    onOpenPokemon: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PokemonViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val details = state.details
    val game = state.game
    when {
        state.loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }

        details == null || game == null -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(stringResource(R.string.pokemon_not_found))
        }

        else -> PokemonContent(
            game = game,
            details = details,
            catch = state.catch,
            onOpenPokemon = onOpenPokemon,
            onShowOnMap = {
                viewModel.showOnMap()
                onShowOnMap()
            },
            onCatchLevel = viewModel::setCatchLevel,
            onCatchHp = viewModel::setCatchHp,
            onCatchStatus = viewModel::setCatchStatus,
            modifier = modifier
        )
    }
}

@Composable
private fun PokemonContent(
    game: Game,
    details: PokemonDetails,
    catch: CatchUiState?,
    onOpenPokemon: (Int) -> Unit,
    onShowOnMap: () -> Unit,
    onCatchLevel: (Int) -> Unit,
    onCatchHp: (HpChoice) -> Unit,
    onCatchStatus: (CatchStatus) -> Unit,
    modifier: Modifier = Modifier
) {
    var movesTab by rememberSaveable(details.id) { mutableIntStateOf(0) }
    LazyColumn(modifier.fillMaxSize()) {
        item { Header(details) }
        section(R.string.pokemon_stats) { Stats(details.stats) }
        section(R.string.pokemon_weaknesses) { Weaknesses(details) }
        section(R.string.pokemon_evolutions) { Evolutions(details, onOpenPokemon) }
        section(R.string.pokemon_locations) { Locations(game, details, onShowOnMap) }
        catch?.let { section(R.string.catch_title) { CatchCalculator(it, onCatchLevel, onCatchHp, onCatchStatus) } }
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
        moves(if (movesTab == 0) details.levelUpMoves else details.machineMoves)
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

@Composable
private fun Header(details: PokemonDetails) {
    var showArtwork by rememberSaveable(details.id) { mutableStateOf(false) }
    var artworkFailed by remember(details.id) { mutableStateOf(false) }
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        Box(Modifier.size(SPRITE_SIZE), contentAlignment = Alignment.Center) {
            if (showArtwork && !artworkFailed) {
                AsyncImage(
                    model = Sprites.officialArtwork(details.id),
                    contentDescription = details.name,
                    filterQuality = FilterQuality.Medium,
                    onError = { artworkFailed = true },
                    modifier = Modifier.fillMaxSize()
                )
            } else {
                AssetImage(details.spritePath ?: details.iconPath, details.name, Modifier.fillMaxSize())
            }
        }
        TextButton(onClick = { showArtwork = !showArtwork }) {
            Icon(
                painterResource(R.drawable.ic_image),
                contentDescription = null,
                modifier = Modifier.padding(end = 8.dp)
            )
            Text(stringResource(if (showArtwork) R.string.pokemon_show_sprite else R.string.pokemon_show_artwork))
        }
        if (showArtwork && artworkFailed) {
            Text(
                stringResource(R.string.pokemon_artwork_error),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
        details.number?.let {
            Text(stringResource(R.string.pokedex_number, it), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(details.name, style = MaterialTheme.typography.headlineMedium)
        Text(
            details.genus,
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { details.types.forEach { TypeBadge(it) } }
        Text(
            stringResource(
                R.string.pokemon_size,
                formatNumber(details.heightDm / 10.0),
                formatNumber(details.weightHg / 10.0)
            ),
            style = MaterialTheme.typography.bodyMedium
        )
        Text(
            stringResource(R.string.pokemon_capture_rate, details.captureRate) + " · " +
                stringResource(R.string.pokemon_growth, details.growthRate),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        details.description?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 8.dp))
        }
    }
}

@Composable
private fun Stats(stats: List<BaseStat>) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        stats.forEach { stat ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(stat.name, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.width(80.dp))
                Text(stat.value.toString(), fontWeight = FontWeight.Bold, modifier = Modifier.width(40.dp))
                LinearProgressIndicator(
                    progress = { stat.value.toFloat() / BaseStat.MAX },
                    modifier = Modifier
                        .weight(1f)
                        .height(8.dp)
                )
            }
        }
        Row {
            Text(stringResource(R.string.pokemon_stats_total), modifier = Modifier.width(80.dp))
            Text(stats.sumOf { it.value }.toString(), fontWeight = FontWeight.Bold)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Weaknesses(details: PokemonDetails) {
    if (details.weaknesses.isEmpty()) {
        Text(stringResource(R.string.pokemon_weaknesses_none))
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        details.weaknesses.groupBy { it.factor }.forEach { (factor, matchups) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(formatFactor(factor), fontWeight = FontWeight.Bold, modifier = Modifier.width(48.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    matchups.forEach { TypeBadge(it.type) }
                }
            }
        }
    }
}

@Composable
private fun Evolutions(details: PokemonDetails, onOpenPokemon: (Int) -> Unit) {
    val single = details.evolutions.singleOrNull()
    if (details.evolutions.isEmpty() || (single != null && single.children.isEmpty())) {
        Text(stringResource(R.string.pokemon_no_evolution))
        return
    }
    Column {
        details.evolutions.forEach { EvolutionBranch(it, details.id, onOpenPokemon) }
    }
}

@Composable
private fun EvolutionBranch(node: EvolutionNode, currentId: Int, onOpenPokemon: (Int) -> Unit) {
    Column {
        val current = node.pokemonId == currentId
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clickable(enabled = !current) { onOpenPokemon(node.pokemonId) }
                .padding(vertical = 2.dp)
        ) {
            AssetImage(Sprites.pokemonIcon(node.pokemonId), contentDescription = null, modifier = Modifier.size(48.dp))
            Text(
                node.name,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = if (current) FontWeight.Bold else FontWeight.Normal,
                color = if (current) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
            )
        }
        // Plusieurs évolutions possibles (Évoli) : chaque branche est décalée.
        val indent = if (node.children.size > 1) 24.dp else 0.dp
        node.children.forEach { child ->
            Column(Modifier.padding(start = indent)) {
                child.condition?.let { EvolutionConditionLabel(it) }
                EvolutionBranch(child, currentId, onOpenPokemon)
            }
        }
    }
}

@Composable
private fun EvolutionConditionLabel(condition: EvolutionCondition) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier.padding(start = 16.dp)
    ) {
        Text("↓", color = MaterialTheme.colorScheme.onSurfaceVariant)
        val identifier = condition.itemIdentifier
        if (identifier != null && condition.itemHasSprite) {
            AssetImage(Sprites.item(identifier), contentDescription = null, modifier = Modifier.size(24.dp))
        }
        val text = when {
            condition.itemName != null -> condition.itemName
            condition.trigger == "trade" -> stringResource(R.string.evolution_trade)
            condition.minLevel != null -> stringResource(R.string.evolution_level, condition.minLevel)
            else -> stringResource(R.string.evolution_level_up)
        }
        Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Locations(game: Game, details: PokemonDetails, onShowOnMap: () -> Unit) {
    val inVersion = details.encounters.filter { it.versionId == game.versionId }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        if (inVersion.isEmpty()) {
            Text(stringResource(R.string.pokemon_locations_none, game.name))
        } else {
            Text(stringResource(R.string.pokemon_locations_in, game.name), style = MaterialTheme.typography.bodyMedium)
            EncounterGroups(inVersion.groupByMethod(), title = { it.areaName })
        }
        if (details.staticEncounters > 0 && inVersion.none { it.isOneOff }) {
            Text(stringResource(R.string.pokemon_locations_static))
        }
        if (details.evolutions.any { root -> root.pokemonId != details.id && root.contains(details.id) }) {
            Text(
                stringResource(R.string.pokemon_locations_evolution),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        val others = details.encounters.filter { it.versionId != game.versionId }.map { it.versionName }.distinct()
        if (others.isNotEmpty()) {
            Text(
                stringResource(R.string.pokemon_locations_other_versions, others.joinToString(", ")),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        if (inVersion.isNotEmpty() || details.staticEncounters > 0) {
            Button(onClick = onShowOnMap, modifier = Modifier.padding(top = 8.dp)) {
                Icon(
                    painterResource(R.drawable.ic_map),
                    contentDescription = null,
                    modifier = Modifier.padding(end = 8.dp)
                )
                Text(stringResource(R.string.pokemon_show_on_map))
            }
        }
    }
}

private fun EvolutionNode.contains(pokemonId: Int): Boolean =
    this.pokemonId == pokemonId || children.any { it.contains(pokemonId) }

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CatchCalculator(
    catch: CatchUiState,
    onLevel: (Int) -> Unit,
    onHp: (HpChoice) -> Unit,
    onStatus: (CatchStatus) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.catch_level, catch.level), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = catch.level.toFloat(),
            onValueChange = { onLevel(it.toInt()) },
            valueRange = 1f..PokemonViewModel.MAX_LEVEL.toFloat()
        )
        Text(stringResource(R.string.catch_hp), style = MaterialTheme.typography.bodyMedium)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            HpChoice.entries.forEach { hp ->
                FilterChip(selected = catch.hp == hp, onClick = {
                    onHp(hp)
                }, label = { Text(stringResource(hp.label)) })
            }
        }
        Text(stringResource(R.string.catch_status), style = MaterialTheme.typography.bodyMedium)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CatchStatus.entries.forEach { status ->
                FilterChip(
                    selected = catch.status == status,
                    onClick = { onStatus(status) },
                    label = { Text(stringResource(status.label)) }
                )
            }
        }
        catch.probabilities.forEach { (ball, probability) ->
            val best = ball == catch.best
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssetImage(
                    Sprites.item(ball.itemIdentifier),
                    contentDescription = null,
                    modifier = Modifier.size(32.dp)
                )
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

private fun LazyListScope.moves(moves: List<LearnedMove>) {
    if (moves.isEmpty()) {
        item { Text(stringResource(R.string.pokemon_moves_none), modifier = Modifier.padding(16.dp)) }
        return
    }
    items(moves, key = { "${it.machine ?: it.level}-${it.moveId}" }) { move ->
        MoveRow(move)
    }
}

@Composable
private fun MoveRow(move: LearnedMove) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                move.machine
                    ?: if (move.level <=
                        1
                    ) {
                        stringResource(R.string.move_start)
                    } else {
                        stringResource(R.string.move_level, move.level)
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

private val SPRITE_SIZE = 160.dp
private val MOVE_TABS = listOf(R.string.pokemon_moves_level, R.string.pokemon_moves_machine)
private const val PERCENT = 100
