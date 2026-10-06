package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.ScaleFactor
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.unit.min
import coil3.asDrawable
import coil3.compose.AsyncImage
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import org.opensources.pokmaps.domain.model.Sprites

/** Sprites animés activés dans les réglages (Pokédex et fiche Pokémon). */
val LocalAnimatedSprites = compositionLocalOf { false }

/**
 * Sprite animé d'un Pokémon (GIF de Noir et Blanc), agrandi d'un nombre entier de fois : pixels nets, et tailles
 * des Pokémon comparables entre eux (un Ronflex reste plus grand qu'un Chenipan). Les plus grands sont réduits
 * pour tenir dans la place disponible.
 */
@Composable
fun AnimatedPokemonSprite(
    pokemonId: Int,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f
) {
    val resources = LocalResources.current
    BoxWithConstraints(modifier, contentAlignment = Alignment.Center) {
        val side = with(LocalDensity.current) { min(maxWidth, maxHeight).toPx() }
        val factor = max(1, (side / ANIMATED_SPRITE_PX).toInt())
        val scale = remember(factor) { IntegerScale(factor.toFloat()) }
        AsyncImage(
            model = Sprites.assetUri(Sprites.pokemonAnimated(pokemonId)),
            contentDescription = contentDescription,
            modifier = Modifier.fillMaxSize(),
            alpha = alpha,
            contentScale = scale,
            filterQuality = FilterQuality.None,
            // Le GIF est dessiné par un Drawable animé : on lui demande aussi de ne pas lisser les pixels.
            onSuccess = { it.result.image.asDrawable(resources).isFilterBitmap = false }
        )
    }
}

/** Agrandit d'un nombre entier de fois (au plus `factor`), ou réduit l'image si elle ne tient pas. */
private class IntegerScale(private val factor: Float) : ContentScale {
    override fun computeScaleFactor(srcSize: Size, dstSize: Size): ScaleFactor {
        val fit = min(dstSize.width / srcSize.width, dstSize.height / srcSize.height)
        val scale = if (fit >= 1f) min(factor, floor(fit)) else fit
        return ScaleFactor(scale, scale)
    }
}

/** Taille de référence des sprites animés (la plupart tiennent dans 96 × 96 pixels). */
private const val ANIMATED_SPRITE_PX = 96f
