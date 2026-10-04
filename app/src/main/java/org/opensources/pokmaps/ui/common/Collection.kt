package org.opensources.pokmaps.ui.common

import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Sprites

/** Poké Ball du Pokédex : pleine si le Pokémon est capturé dans la version, estompée sinon. */
@Composable
fun CaughtButton(caught: Boolean, onToggle: () -> Unit, modifier: Modifier = Modifier) {
    IconButton(onClick = onToggle, modifier = modifier) {
        PixelArtImage(
            Sprites.item(POKE_BALL),
            PixelArt.ITEM_ICON,
            32.dp,
            contentDescription = stringResource(
                if (caught) R.string.collection_caught else R.string.collection_not_caught
            ),
            alpha = if (caught) 1f else NOT_CAUGHT_ALPHA
        )
    }
}

/** Étoile des favoris (communs à tous les jeux). */
@Composable
fun FavoriteButton(favorite: Boolean, onToggle: () -> Unit, modifier: Modifier = Modifier) {
    IconButton(onClick = onToggle, modifier = modifier) {
        Icon(
            painterResource(if (favorite) R.drawable.ic_star else R.drawable.ic_star_outline),
            contentDescription = stringResource(
                if (favorite) R.string.collection_favorite else R.string.collection_not_favorite
            ),
            tint = if (favorite) FAVORITE_COLOR else MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

private const val POKE_BALL = "poke-ball"
private const val NOT_CAUGHT_ALPHA = 0.25f
private val FAVORITE_COLOR = Color(0xFFFFB300)
