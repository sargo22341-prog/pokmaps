package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
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
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.min
import coil3.asDrawable
import coil3.compose.AsyncImage
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites

/** Endroits où les sprites des Pokémon sont animés (réglages). */
val LocalAnimatedPlaces = compositionLocalOf { SpritePlace.DEFAULT_ANIMATED }

/**
 * Taille d'un sprite de Pokémon : au plus `pixel` dp par pixel du sprite, arrondi au nombre entier de pixels de
 * l'écran inférieur (pixels nets, et tailles des Pokémon comparables : un Ronflex reste plus grand qu'un Chenipan),
 * dans un cadre carré de `frame` pixels du sprite où tiennent presque tous les Pokémon (les plus grands y sont
 * réduits).
 */
@Immutable
data class SpriteSize(val pixel: Dp, val frame: Int) {
    companion object {
        /**
         * Listes (Pokémon du lieu sur la carte, recherche) : l'ancien sprite animé de la liste agrandi de 40 %,
         * arrondi au pixel entier (3 pixels de l'écran par pixel du sprite au lieu de 2).
         */
        val LIST = SpriteSize(1.dp, 80)

        /** Fiches (lieux, personnages, dresseurs, objets) et lignes d'évolution : l'échelle de la fiche Pokémon. */
        val SHEET = SpriteSize(1.67.dp, 80)

        /** Grande image de la fiche Pokémon (cadre de 160 dp sur un écran de densité 3), comme [SHEET]. */
        val HEADER = SpriteSize(1.67.dp, 96)

        /** Petite pastille (Pokémon surligné sur la carte). */
        val SMALL = SpriteSize(0.67.dp, 64)
    }
}

/** Sprite d'un Pokémon, animé si les réglages l'animent à cet endroit (`place`), chromatique si `shiny`. */
@Composable
fun PokemonSprite(
    pokemonId: Int,
    place: SpritePlace,
    size: SpriteSize,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f,
    shiny: Boolean = false
) {
    val density = LocalDensity.current
    val factor = max(1, floor(size.pixel.value * density.density).toInt())
    val side = with(density) { (size.frame * factor).toDp() }
    val path = Sprites.pokemon(pokemonId, place in LocalAnimatedPlaces.current, shiny)
    SpriteImage(path, factor, contentDescription, modifier.size(side), alpha)
}

/** Sprite d'un Pokémon aussi grand que possible dans la place disponible (cartes du Pokédex). */
@Composable
fun PokemonSpriteFill(
    pokemonId: Int,
    place: SpritePlace,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f
) {
    PokemonSpriteFill(pokemonId, place in LocalAnimatedPlaces.current, contentDescription, modifier, alpha)
}

/** Sprite d'un Pokémon aussi grand que possible, animé ou fixe quel que soit le réglage (jaquettes des jeux). */
@Composable
fun PokemonSpriteFill(
    pokemonId: Int,
    animated: Boolean,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f
) {
    BoxWithConstraints(modifier, contentAlignment = Alignment.Center) {
        val side = with(LocalDensity.current) { min(maxWidth, maxHeight).toPx() }
        val factor = max(1, (side / FILL_FRAME).toInt())
        SpriteImage(Sprites.pokemon(pokemonId, animated), factor, contentDescription, Modifier.fillMaxSize(), alpha)
    }
}

@Composable
private fun SpriteImage(path: String, factor: Int, contentDescription: String?, modifier: Modifier, alpha: Float) {
    val resources = LocalResources.current
    val scale = remember(factor) { IntegerScale(factor.toFloat()) }
    AsyncImage(
        model = Sprites.assetUri(path),
        contentDescription = contentDescription,
        modifier = modifier,
        alpha = alpha,
        contentScale = scale,
        filterQuality = FilterQuality.None,
        // L'animation est dessinée par un Drawable animé : on lui demande aussi de ne pas lisser les pixels.
        onSuccess = { it.result.image.asDrawable(resources).isFilterBitmap = false }
    )
}

/** Agrandit d'un nombre entier de fois (au plus `factor`), ou réduit l'image si elle ne tient pas. */
private class IntegerScale(private val factor: Float) : ContentScale {
    override fun computeScaleFactor(srcSize: Size, dstSize: Size): ScaleFactor {
        val fit = min(dstSize.width / srcSize.width, dstSize.height / srcSize.height)
        val scale = if (fit >= 1f) min(factor, floor(fit)) else fit
        return ScaleFactor(scale, scale)
    }
}

/** Cadre de référence des sprites qui remplissent leur place (la plupart tiennent dans 96 × 96 pixels). */
private const val FILL_FRAME = 96f
