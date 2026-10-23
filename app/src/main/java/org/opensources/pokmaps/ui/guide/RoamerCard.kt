package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.RoamerArea
import org.opensources.pokmaps.domain.guide.RoamerChoice
import org.opensources.pokmaps.domain.guide.RoamerCondition
import org.opensources.pokmaps.domain.guide.Roamers
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

/** Pokémon errant de la version : condition d'apparition, niveau et routes parcourues. */
@Composable
internal fun RoamerCard(
    roamer: RoamerChoice,
    version: Int,
    observation: String? = null,
    onObserve: (String?) -> Unit = {}
) {
    val name = stringResource(pokemonLabel(roamer.pokemonId))
    Card(Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            PokemonSprite(roamer.pokemonId, SpritePlace.POKEMON_SHEET, SpriteSize.LIST, name)
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(name, style = MaterialTheme.typography.titleMedium)
                Text(stringResource(roamer.condition.label()), style = MaterialTheme.typography.bodyMedium)
                Text(stringResource(R.string.catch_level, Roamers.level(version, roamer.pokemonId)))
                Text(
                    stringResource(Roamers.area(version, roamer.pokemonId).label()),
                    style = MaterialTheme.typography.bodySmall
                )
                if (version in 12..16) RoamerObservation(version, roamer.pokemonId, observation, onObserve)
            }
        }
    }
}

private fun pokemonLabel(pokemon: Int): Int = when (pokemon) {
    481 -> R.string.guide_roamer_mesprit
    488 -> R.string.guide_roamer_cresselia
    144 -> R.string.guide_roamer_articuno
    145 -> R.string.guide_roamer_zapdos
    146 -> R.string.guide_roamer_moltres
    243 -> R.string.guide_roamer_raikou
    244 -> R.string.guide_roamer_entei
    245 -> R.string.guide_roamer_suicune
    380 -> R.string.guide_roamer_latias
    381 -> R.string.guide_roamer_latios
    else -> error("Pokémon errant inconnu : $pokemon")
}

private fun RoamerCondition.label(): Int = when (this) {
    RoamerCondition.HGSS_EON -> R.string.guide_roamer_hgss_eon
    RoamerCondition.MESPRIT -> R.string.guide_roamer_mesprit_condition
    RoamerCondition.CRESSELIA -> R.string.guide_roamer_cresselia_condition
    RoamerCondition.BIRDS -> R.string.guide_roamer_birds_condition
    RoamerCondition.JOHTO -> R.string.guide_roamer_johto
    RoamerCondition.HOENN -> R.string.guide_roamer_hoenn
    RoamerCondition.RED -> R.string.guide_roamer_red
    RoamerCondition.BLUE -> R.string.guide_roamer_blue
    RoamerCondition.BULBASAUR -> R.string.guide_roamer_bulbasaur
    RoamerCondition.CHARMANDER -> R.string.guide_roamer_charmander
    RoamerCondition.SQUIRTLE -> R.string.guide_roamer_squirtle
}

private fun RoamerArea.label(): Int = when (this) {
    RoamerArea.SINNOH -> R.string.guide_roamer_area_sinnoh
    RoamerArea.JOHTO -> R.string.guide_roamer_area_johto
    RoamerArea.HOENN -> R.string.guide_roamer_area_hoenn
    RoamerArea.KANTO -> R.string.guide_roamer_area_kanto
}
