package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.HeldItem
import org.opensources.pokmaps.domain.pokemon.PokemonTraits
import org.opensources.pokmaps.domain.pokemon.ShinyOdds
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.formatNumber

// Sections des mécaniques apparues après la 1re génération (GenerationFeature) : objets tenus et chromatiques
// sont toujours affichés (avec l'explication de leur absence), sexe, œufs et talents seulement si le jeu les connaît.

/** Objets que tient le Pokémon sauvage dans la version, avec leur probabilité ; vers la fiche de l'objet. */
@Composable
internal fun HeldItems(state: PokemonUiState, game: Game, traits: PokemonTraits, onOpenItem: (String) -> Unit) {
    when {
        !state.has(
            GenerationFeature.HELD_ITEMS
        ) -> MutedText(stringResource(R.string.pokemon_held_items_absent, game.name))

        traits.heldItems.isEmpty() -> Text(stringResource(R.string.pokemon_held_items_none, game.name))

        else -> Column { traits.heldItems.forEach { HeldItemRow(it, onOpenItem) } }
    }
}

@Composable
private fun HeldItemRow(item: HeldItem, onOpenItem: (String) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenItem(item.identifier) }
            .padding(vertical = 4.dp)
    ) {
        if (item.hasSprite) PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 40.dp, null)
        Text(item.name, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Text(
            stringResource(R.string.encounter_chance, formatNumber(item.rarity.toDouble())),
            fontWeight = FontWeight.Bold
        )
    }
}

/** Probabilité de rencontrer le Pokémon en chromatique, ou absence des chromatiques dans le jeu. */
@Composable
internal fun ShinyOddsText(state: PokemonUiState, game: Game) {
    val odds = state.shinyOdds
    if (odds == null) {
        MutedText(
            stringResource(R.string.pokemon_shiny_absent, game.name, formatNumber(ShinyOdds.FIRST_ODDS.toDouble()))
        )
    } else {
        Text(stringResource(R.string.pokemon_shiny_odds, formatNumber(odds.toDouble()), game.name))
    }
}

/** Proportion de mâles et de femelles, ou asexué. */
@Composable
internal fun Gender(traits: PokemonTraits) {
    val text = when (val gender = traits.gender) {
        GenderRatio.Genderless -> stringResource(R.string.pokemon_genderless)

        is GenderRatio.Gendered -> stringResource(
            R.string.pokemon_gender_ratio,
            formatNumber(gender.malePercent),
            formatNumber(gender.femalePercent)
        )
    }
    Text(text)
}

/** Groupes d'œufs et cycles d'éclosion. */
@Composable
internal fun Breeding(traits: PokemonTraits) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            if (traits.eggGroups.isEmpty()) {
                stringResource(R.string.pokemon_no_egg_group)
            } else {
                stringResource(R.string.pokemon_egg_groups, traits.eggGroups.joinToString(", "))
            }
        )
        Text(stringResource(R.string.pokemon_hatch_cycles, traits.hatchCycles))
    }
}

/** Talents du Pokémon dans la génération, avec leur description dans le jeu. */
@Composable
internal fun Abilities(traits: PokemonTraits) {
    if (traits.abilities.isEmpty()) {
        Text(stringResource(R.string.pokemon_abilities_none))
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        traits.abilities.forEach { ability ->
            Column {
                Text(
                    if (ability.hidden) stringResource(R.string.pokemon_ability_hidden, ability.name) else ability.name,
                    style = MaterialTheme.typography.titleSmall
                )
                ability.description?.let { MutedText(it) }
            }
        }
    }
}

@Composable
private fun MutedText(text: String) {
    Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
