package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.layout.FixedScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.max
import coil3.asDrawable
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.size.Size as CoilSize
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.PixelArt
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.ui.state.MapState

// Les marqueurs sont dessinés à l'échelle de la carte : un pixel d'un sprite vaut un pixel Game Boy de la carte,
// ils grandissent et rapetissent avec elle (un personnage occupe une case, comme dans le jeu).

/** Taille à l'écran de `pixels` pixels de la carte, au zoom actuel. */
@Composable
private fun mapPixels(mapState: MapState, pixels: Float): Dp {
    val scale by remember(mapState) { derivedStateOf { mapState.scale } }
    return with(LocalDensity.current) { (pixels * scale).toFloat().toDp() }
}

/** Les marqueurs des calques ne s'affichent qu'à partir d'un certain zoom, pour ne pas surcharger la carte. */
@Composable
private fun visibleAtScale(mapState: MapState): Boolean {
    val visible by remember(mapState) { derivedStateOf { mapState.scale >= MIN_MARKER_SCALE } }
    return visible
}

/** Entrée (porte, escalier, grotte) : on la touche pour entrer (une case autour du point suffit). */
@Composable
fun WarpMarker(mapState: MapState, alwaysVisible: Boolean = false) {
    if (!alwaysVisible && !visibleAtScale(mapState)) return
    val tile = mapPixels(mapState, TILE_PX)
    val dot = max(mapPixels(mapState, WARP_PX), WARP_MIN_SIZE)
    Box(Modifier.size(max(tile, dot)), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(dot)
                .background(WARP_COLOR.copy(alpha = 0.85f), CircleShape)
                .border(dot / 7, Color.White, CircleShape)
        )
    }
}

/**
 * Objet (avec son icône), objet caché, dresseur, personnage ou Pokémon fixe, à la taille `scale` choisie selon la
 * place autour de lui (voir MarkerSizing) ; Pokémon animé si `animated`.
 */
@Composable
fun ObjectMarker(
    mapState: MapState,
    obj: MapObject,
    versionGroupIdentifier: String,
    alwaysVisible: Boolean = false,
    scale: Float = 1f,
    animated: Boolean = false
) {
    if (!alwaysVisible && !visibleAtScale(mapState)) return
    val sprite = obj.sprite
    val itemIdentifier = obj.itemIdentifier
    val pokemonId = obj.pokemonId
    Box {
        when {
            itemIdentifier != null -> AssetImage(
                Sprites.item(itemIdentifier),
                contentDescription = obj.itemName,
                modifier = Modifier.size(mapPixels(mapState, PixelArt.ITEM_ICON, scale)),
                alpha = if (obj.kind == MapObjectKind.HIDDEN_ITEM) HIDDEN_ALPHA else 1f
            )

            obj.kind == MapObjectKind.POKEMON && pokemonId != null -> MapPokemon(
                mapState,
                pokemonId,
                obj.pokemonName,
                scale,
                animated
            )

            sprite != null -> AssetImage(
                Sprites.mapSprite(versionGroupIdentifier, sprite),
                contentDescription = null,
                modifier = Modifier.size(mapPixels(mapState, PixelArt.MAP_SPRITE, scale))
            )

            else -> Box(Modifier.size(mapPixels(mapState, TILE_PX / 2 * scale)).background(Color.White, CircleShape))
        }
        when (obj.kind) {
            MapObjectKind.HIDDEN_ITEM -> Badge(mapState, "?", HIDDEN_COLOR, Modifier.align(Alignment.BottomEnd), scale)
            MapObjectKind.TRAINER -> Badge(mapState, "!", TRAINER_COLOR, Modifier.align(Alignment.TopEnd), scale)
            else -> Unit
        }
    }
}

/** Pokémon sauvage, dessiné là où on le rencontre (herbes, eau, sol des grottes) ; animé si `animated`. */
@Composable
fun WildPokemonMarker(mapState: MapState, wild: WildMarker, animated: Boolean = false) {
    Box {
        MapPokemon(mapState, wild.pokemonId, wild.name, wild.scale, animated)
        val corner = Modifier.align(Alignment.BottomEnd)
        when (wild.method) {
            WildMethod.FISHING -> Badge(mapState, "🎣", WATER_COLOR, corner, wild.scale)
            WildMethod.SURF -> Badge(mapState, "🌊", WATER_COLOR, corner, wild.scale)
            WildMethod.WALK -> Unit
        }
    }
}

/**
 * Pokémon dessiné à l'échelle de la carte : son icône de boîte, ou son sprite animé de Noir et Blanc. Un pixel du
 * sprite animé vaut [ANIMATED_RATIO] pixel de la carte : les Pokémon gardent leurs tailles relatives (un Ronflex
 * reste plus grand qu'un Chenipan) et occupent à peu près la place de leur icône. Le sprite est centré dans son
 * cadre (de la taille du plus grand sprite).
 */
@Composable
private fun MapPokemon(
    mapState: MapState,
    pokemonId: Int,
    contentDescription: String?,
    scale: Float,
    animated: Boolean
) {
    if (!animated) {
        AssetImage(
            Sprites.pokemonIcon(pokemonId),
            contentDescription = contentDescription,
            modifier = Modifier.size(mapPixels(mapState, PixelArt.POKEMON_ICON, scale))
        )
        return
    }
    val context = LocalContext.current
    val mapScale by remember(mapState) { derivedStateOf { mapState.scale } }
    // Le GIF est lu à sa taille d'origine, puis agrandi d'un facteur fixe (et non ajusté à son cadre).
    val request = remember(pokemonId) {
        ImageRequest.Builder(context)
            .data(Sprites.assetUri(Sprites.pokemonAnimated(pokemonId)))
            .size(CoilSize.ORIGINAL)
            .build()
    }
    val factor = (mapScale * ANIMATED_RATIO * scale).toFloat()
    AsyncImage(
        model = request,
        contentDescription = contentDescription,
        modifier = Modifier.size(mapPixels(mapState, ANIMATED_FRAME_PX * ANIMATED_RATIO * scale)),
        contentScale = remember(factor) { FixedScale(factor) },
        filterQuality = FilterQuality.None,
        onSuccess = { it.result.image.asDrawable(context.resources).isFilterBitmap = false }
    )
}

@Composable
private fun mapPixels(mapState: MapState, source: PixelArt.Source, scale: Float = 1f): DpSize =
    DpSize(mapPixels(mapState, source.width * scale), mapPixels(mapState, source.height * scale))

/** Pastille ronde avec un symbole, dans un coin du marqueur, elle aussi à l'échelle de la carte. */
@Composable
private fun Badge(mapState: MapState, text: String, color: Color, modifier: Modifier = Modifier, scale: Float = 1f) {
    val size = mapPixels(mapState, BADGE_PX * scale)
    val fontSize = with(LocalDensity.current) { (size * 0.6f).toSp() }
    Box(
        modifier
            .size(size)
            .background(color, CircleShape)
            .border(size / 16, Color.White, CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = Color.White, fontSize = fontSize, fontWeight = FontWeight.Bold, lineHeight = fontSize)
    }
}

/** Lieu surligné (entrée d'une carte intérieure ou Pokémon fixe) : anneau bien visible à tout zoom. */
@Composable
fun HighlightMarker() {
    Box(
        Modifier
            .size(28.dp)
            .background(HIGHLIGHT_COLOR.copy(alpha = 0.35f), CircleShape)
            .border(3.dp, HIGHLIGHT_COLOR, CircleShape)
    )
}

val HIGHLIGHT_COLOR = Color(0xFFFF1744)
private val WARP_COLOR = Color(0xFF2962FF)
private val HIDDEN_COLOR = Color(0xFF6A1B9A)
private val TRAINER_COLOR = Color(0xFFD32F2F)
private val WATER_COLOR = Color(0xFF0277BD)
private val WARP_MIN_SIZE = 8.dp

/** Taille d'un pixel des sprites animés, en pixels de la carte : leur dessin a à peu près la taille d'une icône. */
private const val ANIMATED_RATIO = 0.75f

/** Cadre des sprites animés de Noir et Blanc (le plus grand tient dans 96 × 96 pixels). */
private const val ANIMATED_FRAME_PX = 96f

/** Tailles en pixels de la carte (une case du jeu fait 16 pixels). */
private const val TILE_PX = 16f
private const val WARP_PX = 9f
private const val BADGE_PX = 8f
private const val HIDDEN_ALPHA = 0.75f
private const val MIN_MARKER_SCALE = 1.0
