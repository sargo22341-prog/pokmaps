package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.min
import kotlin.math.max
import kotlin.math.roundToInt

/** Tailles des images embarquées, en pixels. */
object PixelArt {
    /** Icône de boîte d'un Pokémon (pokesprite). */
    val POKEMON_ICON = Source(68, 56)

    /**
     * Le Pokémon est dessiné en bas de son icône, sur environ la moitié de sa largeur : centre du dessin et part
     * de l'icône qu'il occupe, relatifs à la taille de l'icône (moyennes sur les 151 icônes).
     */
    const val POKEMON_CENTER_Y = 0.71f
    const val POKEMON_CONTENT_WIDTH = 0.62f
    const val POKEMON_CONTENT_HEIGHT = 0.78f

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

/**
 * Image pixel-art aussi grande que possible dans la largeur disponible (au plus `widthLimit`),
 * agrandie d'un nombre entier de fois.
 */
@Composable
fun PixelArtFill(
    path: String,
    source: PixelArt.Source,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    widthLimit: Dp = Dp.Infinity,
    alpha: Float = 1f
) {
    BoxWithConstraints(modifier, contentAlignment = Alignment.Center) {
        val density = LocalDensity.current
        val available = with(density) { min(maxWidth, widthLimit).toPx() }
        val factor = max(1, (available / source.width).toInt())
        val size = with(density) { DpSize((source.width * factor).toDp(), (source.height * factor).toDp()) }
        AssetImage(path, contentDescription, Modifier.size(size), alpha = alpha)
    }
}

/**
 * Icône d'un Pokémon cadrée sur son dessin : les marges transparentes de l'icône (au-dessus et sur les côtés)
 * débordent de la place occupée, pour serrer les listes et les évolutions. Agrandie d'un nombre entier de fois.
 */
@Composable
fun PokemonIconImage(
    path: String,
    targetWidth: Dp,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f
) {
    val size = pixelArtSize(PixelArt.POKEMON_ICON, targetWidth)
    Box(modifier.size(size.width * PixelArt.POKEMON_CONTENT_WIDTH, size.height * PixelArt.POKEMON_CONTENT_HEIGHT)) {
        AssetImage(
            path,
            contentDescription,
            Modifier
                .wrapContentSize(Alignment.BottomCenter, unbounded = true)
                .size(size),
            alpha = alpha
        )
    }
}
