package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.pokemon.BaseStat
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionNode
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonIconImage
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.formatFactor

private val BRANCH_SPACING = 8.dp

@Composable
internal fun Stats(stats: List<BaseStat>) {
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
internal fun Weaknesses(details: PokemonDetails) {
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
internal fun Evolutions(details: PokemonDetails, onOpenPokemon: (Int) -> Unit, onOpenItem: (String) -> Unit) {
    val single = details.evolutions.singleOrNull()
    if (details.evolutions.isEmpty() || (single != null && single.children.isEmpty())) {
        Text(stringResource(R.string.pokemon_no_evolution))
        return
    }
    // Arbre de gauche à droite : chaque évolution part de son Pokémon d'origine, avec sa condition sur la flèche.
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.horizontalScroll(rememberScrollState())
    ) {
        details.evolutions.forEach { EvolutionTreeNode(it, details.id, onOpenPokemon, onOpenItem) }
    }
}

@Composable
private fun EvolutionTreeNode(
    node: EvolutionNode,
    currentId: Int,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        EvolutionMember(node, currentId, onOpenPokemon)
        if (node.children.isNotEmpty()) {
            EvolutionBranches(node.children, currentId, onOpenPokemon, onOpenItem)
        }
    }
}

/** Évolutions d'un Pokémon, l'une sous l'autre ; plusieurs (Évoli) sont reliées par un trait vertical. */
@Composable
private fun EvolutionBranches(
    children: List<EvolutionNode>,
    currentId: Int,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit
) {
    val branchColor = MaterialTheme.colorScheme.outline
    val count = children.size
    Column(
        verticalArrangement = Arrangement.spacedBy(BRANCH_SPACING),
        modifier = Modifier.drawBehind {
            // Plusieurs évolutions possibles (Évoli) : une accolade relie les branches à leur origine.
            if (count > 1) {
                val rowHeight = (size.height - BRANCH_SPACING.toPx() * (count - 1)) / count
                val top = rowHeight / 2
                val bottom = size.height - rowHeight / 2
                val stroke = 2.dp.toPx()
                drawLine(branchColor, Offset(stroke / 2, top), Offset(stroke / 2, bottom), stroke)
            }
        }
    ) {
        children.forEach { child ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                EvolutionArrow(child.condition, branchColor, onOpenItem)
                EvolutionTreeNode(child, currentId, onOpenPokemon, onOpenItem)
            }
        }
    }
}

@Composable
private fun EvolutionMember(node: EvolutionNode, currentId: Int, onOpenPokemon: (Int) -> Unit) {
    val current = node.pokemonId == currentId
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .widthIn(min = 72.dp)
            .clickable(enabled = !current) { onOpenPokemon(node.pokemonId) }
            .padding(4.dp)
    ) {
        // Icône cadrée sur le Pokémon : ses marges transparentes n'écartent plus les flèches.
        PokemonIconImage(Sprites.pokemonIcon(node.pokemonId), 128.dp, contentDescription = null)
        Text(
            node.name,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = if (current) FontWeight.Bold else FontWeight.Normal,
            color = if (current) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
        )
    }
}

/** Flèche vers une évolution, avec sa condition : niveau, pierre (avec son icône, vers sa fiche) ou échange. */
@Composable
private fun EvolutionArrow(condition: EvolutionCondition?, color: Color, onOpenItem: (String) -> Unit) {
    val identifier = condition?.itemIdentifier
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .width(72.dp)
            .clickable(enabled = identifier != null) { identifier?.let(onOpenItem) }
    ) {
        if (condition != null && identifier != null && condition.itemHasSprite) {
            PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 56.dp, contentDescription = null)
        }
        val text = when {
            condition == null -> ""
            condition.itemName != null -> condition.itemName
            condition.trigger == "trade" -> stringResource(R.string.evolution_trade)
            condition.minLevel != null -> stringResource(R.string.evolution_level, condition.minLevel)
            else -> stringResource(R.string.evolution_level_up)
        }
        Text(
            text,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        Text("⟶", color = color, style = MaterialTheme.typography.titleLarge)
    }
}

@Composable
internal fun Locations(game: Game, details: PokemonDetails, onShowOnMap: () -> Unit) {
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
