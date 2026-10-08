package org.opensources.pokmaps.ui.map

import androidx.annotation.DrawableRes
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
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
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.max
import coil3.asDrawable
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.size.Size as CoilSize
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.LocalAnimatedPlaces
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.facilityIcon
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
 * Objet (avec son icône), objet caché, dresseur, personnage, Pokémon fixe ou installation, à la taille `scale`
 * choisie selon la place autour de lui (voir MarkerSizing).
 */
@Composable
fun ObjectMarker(
    mapState: MapState,
    obj: MapObject,
    versionGroupIdentifier: String,
    alwaysVisible: Boolean = false,
    scale: Float = 1f
) {
    if (!alwaysVisible && !visibleAtScale(mapState)) return
    val sprite = obj.sprite
    val itemIdentifier = obj.fruit?.identifier ?: obj.itemIdentifier
    val pokemonId = obj.pokemonId
    val facility = obj.kind.facilityIcon
    Box {
        when {
            itemIdentifier != null && (obj.fruit?.hasSprite ?: obj.itemHasSprite) -> AssetImage(
                Sprites.item(itemIdentifier),
                contentDescription = obj.fruit?.name ?: obj.itemName,
                modifier = Modifier.size(mapPixels(mapState, PixelArt.ITEM_ICON, scale)),
                alpha = if (obj.kind == MapObjectKind.HIDDEN_ITEM) HIDDEN_ALPHA else 1f
            )

            obj.kind == MapObjectKind.POKEMON && pokemonId != null ->
                MapPokemon(mapState, pokemonId, obj.pokemonName, scale, obj.shiny)

            sprite != null -> AssetImage(
                Sprites.mapSprite(versionGroupIdentifier, sprite),
                contentDescription = null,
                modifier = Modifier.size(mapPixels(mapState, PixelArt.MAP_SPRITE, scale))
            )

            facility != null -> FacilityMarker(mapState, facility, obj.name, scale)

            else -> Box(Modifier.size(mapPixels(mapState, TILE_PX / 2 * scale)).background(Color.White, CircleShape))
        }
        KindBadge(mapState, obj.kind, scale)
    }
}

/** Repère d'un objet caché (« ? ») ou d'un dresseur (« ! »), dans un coin du marqueur. */
@Composable
private fun BoxScope.KindBadge(mapState: MapState, kind: MapObjectKind, scale: Float) {
    when (kind) {
        MapObjectKind.HIDDEN_ITEM -> Badge(
            mapState,
            stringResource(R.string.map_badge_hidden),
            HIDDEN_COLOR,
            Modifier.align(Alignment.BottomEnd),
            scale
        )

        MapObjectKind.TRAINER -> Badge(
            mapState,
            stringResource(R.string.map_badge_trainer),
            TRAINER_COLOR,
            Modifier.align(Alignment.TopEnd),
            scale
        )

        MapObjectKind.ITEM, MapObjectKind.POKEMON, MapObjectKind.NPC, MapObjectKind.NPC_OBJECT,
        MapObjectKind.NPC_POKEMON, MapObjectKind.VENDING_MACHINE, MapObjectKind.PRIZE_VENDOR,
        MapObjectKind.HEAL_SPOT -> Unit
    }
}

/** Installation (distributeur, comptoir des lots, soins) : son icône sur une pastille, de la taille d'une case. */
@Composable
private fun FacilityMarker(mapState: MapState, @DrawableRes icon: Int, name: String, scale: Float) {
    val size = mapPixels(mapState, TILE_PX * scale)
    val shape = RoundedCornerShape(size / 4)
    Box(
        Modifier
            .size(size)
            .background(FACILITY_COLOR, shape)
            .border(size / 16, Color.White, shape),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            painterResource(icon),
            contentDescription = name,
            tint = Color.White,
            modifier = Modifier.size(size * 0.7f)
        )
    }
}

/** Pokémon sauvage, dessiné là où on le rencontre (herbes, eau, sol des grottes). */
@Composable
fun WildPokemonMarker(mapState: MapState, wild: WildMarker) {
    MapPokemon(mapState, wild.pokemonId, wild.name, wild.scale)
}

/**
 * Pokémon dessiné à l'échelle de la carte : son sprite de Noir et Blanc, animé ou fixe selon le réglage de la carte
 * (même image, même taille). Un pixel du sprite vaut [POKEMON_RATIO] pixel de la carte : les Pokémon gardent leurs
 * tailles relatives (un Ronflex reste plus grand qu'un Chenipan). Le sprite est centré dans son cadre, de la taille
 * du plus grand sprite.
 */
@Composable
private fun MapPokemon(
    mapState: MapState,
    pokemonId: Int,
    contentDescription: String?,
    scale: Float,
    shiny: Boolean = false
) {
    val context = LocalContext.current
    val resources = LocalResources.current
    val animated = SpritePlace.MAP in LocalAnimatedPlaces.current
    val mapScale by remember(mapState) { derivedStateOf { mapState.scale } }
    // Le sprite est lu à sa taille d'origine, puis agrandi d'un facteur fixe (et non ajusté à son cadre).
    val request = remember(pokemonId, animated, shiny) {
        ImageRequest.Builder(context)
            .data(Sprites.assetUri(Sprites.pokemon(pokemonId, animated, shiny)))
            .size(CoilSize.ORIGINAL)
            .build()
    }
    val factor = (mapScale * POKEMON_RATIO * scale).toFloat()
    AsyncImage(
        model = request,
        contentDescription = contentDescription,
        modifier = Modifier.size(mapPixels(mapState, POKEMON_FRAME_PX * POKEMON_RATIO * scale)),
        contentScale = remember(factor) { FixedScale(factor) },
        filterQuality = FilterQuality.None,
        onSuccess = { it.result.image.asDrawable(resources).isFilterBitmap = false }
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
private val FACILITY_COLOR = Color(0xFF00897B)
private val WARP_MIN_SIZE = 8.dp

/**
 * Taille d'un pixel des sprites des Pokémon, en pixels de la carte : 0,75 augmenté de 30 %, pour que les sprites de
 * Noir et Blanc aient à peu près la taille des anciennes icônes fixes.
 */
private const val POKEMON_RATIO = 0.6825f

/** Cadre des sprites de Noir et Blanc : le plus grand tient dans 128 × 128 pixels. */
private const val POKEMON_FRAME_PX = 128f

/** Tailles en pixels de la carte (une case du jeu fait 16 pixels). */
private const val TILE_PX = 16f
private const val WARP_PX = 9f
private const val BADGE_PX = 8f
private const val HIDDEN_ALPHA = 0.75f
private const val MIN_MARKER_SCALE = 1.0
