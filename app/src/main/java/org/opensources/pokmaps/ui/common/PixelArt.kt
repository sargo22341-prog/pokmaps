package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import kotlin.math.max
import kotlin.math.roundToInt

/** Tailles des images embarquées, en pixels. */
object PixelArt {
    /** Icône de boîte d'un Pokémon (pokesprite). */
    val POKEMON_ICON = Source(68, 56)

    /** Icône d'objet (pokesprite). */
    val ITEM_ICON = Source(32, 32)

    /** Sprite d'un personnage ou d'un objet sur la carte (pret). */
    val MAP_SPRITE = Source(16, 16)

    data class Source(val width: Int, val height: Int)
}

/**
 * Taille d'affichage d'une image pixel-art proche de `targetWidth`, agrandie d'un nombre entier de fois en pixels
 * de l'écran : chaque pixel du sprite garde la même taille, sans déformation.
 */
@Composable
fun pixelArtSize(source: PixelArt.Source, targetWidth: Dp): DpSize {
    val density = LocalDensity.current
    val factor = max(1, (targetWidth.value * density.density / source.width).roundToInt())
    return with(density) { DpSize((source.width * factor).toDp(), (source.height * factor).toDp()) }
}

/** Image pixel-art des assets à une taille entière (voir [pixelArtSize]). */
@Composable
fun PixelArtImage(
    path: String,
    source: PixelArt.Source,
    targetWidth: Dp,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f
) {
    val size = pixelArtSize(source, targetWidth)
    AssetImage(path, contentDescription, modifier.size(size), alpha = alpha)
}
