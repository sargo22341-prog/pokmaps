package org.opensources.pokmaps.ui.common

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
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

/** Petite Poké Ball : Pokémon déjà capturé dans la version. */
@Composable
fun CaughtIcon(size: Dp, modifier: Modifier = Modifier) {
    PixelArtImage(
        Sprites.item(POKE_BALL),
        PixelArt.ITEM_ICON,
        size,
        contentDescription = stringResource(R.string.collection_caught),
        modifier = modifier
    )
}

/** Master Ball : tous les Pokémon sauvages du lieu sont capturés. */
@Composable
fun CompleteIcon(size: Dp, modifier: Modifier = Modifier) {
    PixelArtImage(
        Sprites.item(MASTER_BALL),
        PixelArt.ITEM_ICON,
        size,
        contentDescription = stringResource(R.string.map_zone_complete),
        modifier = modifier
    )
}

/**
 * Pokémon sauvages capturés : Poké Ball et « 1/2 », ou Master Ball et coche quand le lieu est terminé
 * (tous capturés), avec une petite animation au moment où il le devient.
 */
@Composable
fun CaughtProgress(caught: Int, total: Int, modifier: Modifier = Modifier) {
    AnimatedContent(
        targetState = caught >= total,
        transitionSpec = { (scaleIn() + fadeIn()) togetherWith fadeOut() },
        label = "progress"
    ) { complete ->
        Row(verticalAlignment = Alignment.CenterVertically, modifier = modifier) {
            if (complete) {
                CompleteIcon(PROGRESS_ICON)
                Icon(
                    painterResource(R.drawable.ic_check),
                    contentDescription = stringResource(R.string.map_zone_complete),
                    tint = COMPLETE_COLOR,
                    modifier = Modifier.size(16.dp)
                )
            } else {
                CaughtIcon(PROGRESS_ICON)
                Text(
                    stringResource(R.string.map_zone_caught, caught, total),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

private val PROGRESS_ICON = 24.dp
private val COMPLETE_COLOR = Color(0xFF43A047)
private const val POKE_BALL = "poke-ball"
private const val MASTER_BALL = "master-ball"
private const val NOT_CAUGHT_ALPHA = 0.25f
private val FAVORITE_COLOR = Color(0xFFFFB300)
