package org.opensources.pokmaps.ui.game

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.ui.common.PokemonSpriteFill

/**
 * Jaquette d'un jeu, dessinée aux couleurs de la version avec le Pokémon de sa jaquette (Dracaufeu, Tortank,
 * Pikachu…), sans titre visible.
 */
@Composable
internal fun GameCover(game: Game, modifier: Modifier = Modifier) {
    val color = Color(COLOR_ALPHA or game.color)
    val description = stringResource(R.string.game_cover, game.name)
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween,
        modifier = modifier
            .size(COVER_WIDTH, COVER_HEIGHT)
            .clip(COVER_SHAPE)
            .background(Brush.verticalGradient(listOf(lerp(color, Color.White, LIGHTEN), color)))
            .border(1.dp, lerp(color, Color.Black, DARKEN), COVER_SHAPE)
            .padding(vertical = 4.dp)
            .semantics { contentDescription = description }
    ) {
        // Une jaquette est une image : le Pokémon y reste fixe.
        PokemonSpriteFill(game.mascotPokemonId, animated = false, contentDescription = null, Modifier.weight(1f))
    }
}

private val COVER_WIDTH = 88.dp
private val COVER_HEIGHT = 104.dp
private val COVER_SHAPE = RoundedCornerShape(6.dp)
private const val COLOR_ALPHA = 0xFF000000.toInt()
private const val LIGHTEN = 0.35f
private const val DARKEN = 0.4f
