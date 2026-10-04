package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.ui.state.MapState

// Les marqueurs gardent la même taille à l'écran quel que soit le zoom (ils ne sont pas agrandis avec la carte),
// et les sprites sont agrandis d'un nombre entier de fois pour que leurs pixels restent nets et réguliers.

/** Les marqueurs des calques ne s'affichent qu'à partir d'un certain zoom, pour ne pas surcharger la carte. */
@Composable
private fun visibleAtScale(mapState: MapState): Boolean {
    val visible by remember(mapState) { derivedStateOf { mapState.scale >= MIN_MARKER_SCALE } }
    return visible
}

/** Entrée (porte, escalier, grotte) : on la touche pour entrer. La zone de toucher dépasse largement le point. */
@Composable
fun WarpMarker(mapState: MapState, alwaysVisible: Boolean = false) {
    if (!alwaysVisible && !visibleAtScale(mapState)) return
    Box(Modifier.size(WARP_TOUCH_SIZE), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(14.dp)
                .background(WARP_COLOR.copy(alpha = 0.85f), CircleShape)
                .border(2.dp, Color.White, CircleShape)
        )
    }
}

/** Objet (avec son icône), objet caché, dresseur, personnage ou Pokémon fixe. */
@Composable
fun ObjectMarker(mapState: MapState, obj: MapObject, versionGroupIdentifier: String, alwaysVisible: Boolean = false) {
    if (!alwaysVisible && !visibleAtScale(mapState)) return
    val sprite = obj.sprite
    val itemIdentifier = obj.itemIdentifier
    val pokemonId = obj.pokemonId
    Box {
        when {
            itemIdentifier != null -> PixelArtImage(
                Sprites.item(itemIdentifier),
                PixelArt.ITEM_ICON,
                ITEM_SIZE,
                contentDescription = obj.itemName,
                alpha = if (obj.kind == MapObjectKind.HIDDEN_ITEM) HIDDEN_ALPHA else 1f
            )

            obj.kind == MapObjectKind.POKEMON && pokemonId != null -> PixelArtImage(
                Sprites.pokemonIcon(pokemonId),
                PixelArt.POKEMON_ICON,
                POKEMON_SIZE,
                contentDescription = obj.pokemonName
            )

            sprite != null -> PixelArtImage(
                Sprites.mapSprite(versionGroupIdentifier, sprite),
                PixelArt.MAP_SPRITE,
                CHARACTER_SIZE,
                contentDescription = null
            )

            else -> Box(Modifier.size(12.dp).background(Color.White, CircleShape))
        }
        when (obj.kind) {
            MapObjectKind.HIDDEN_ITEM -> Badge("?", HIDDEN_COLOR, Modifier.align(Alignment.BottomEnd))
            MapObjectKind.TRAINER -> Badge("!", TRAINER_COLOR, Modifier.align(Alignment.TopEnd))
            else -> Unit
        }
    }
}

/** Pokémon sauvage, dessiné là où on le rencontre (herbes, eau, sol des grottes). */
@Composable
fun WildPokemonMarker(wild: WildMarker) {
    Box {
        PixelArtImage(
            Sprites.pokemonIcon(wild.pokemonId),
            PixelArt.POKEMON_ICON,
            POKEMON_SIZE,
            contentDescription = wild.name
        )
        when (wild.method) {
            WildMethod.FISHING -> Badge("🎣", WATER_COLOR, Modifier.align(Alignment.BottomEnd))
            WildMethod.SURF -> Badge("🌊", WATER_COLOR, Modifier.align(Alignment.BottomEnd))
            WildMethod.WALK -> Unit
        }
    }
}

/** Pastille ronde avec un symbole, dans un coin du marqueur. */
@Composable
private fun Badge(text: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier
            .size(16.dp)
            .background(color, CircleShape)
            .border(1.dp, Color.White, CircleShape)
            .padding(1.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(text, color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.Bold, lineHeight = 9.sp)
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
private val WARP_TOUCH_SIZE = 40.dp
private val ITEM_SIZE = 28.dp
private val CHARACTER_SIZE = 28.dp
private val POKEMON_SIZE = 52.dp
private const val HIDDEN_ALPHA = 0.75f
private const val MIN_MARKER_SCALE = 1.0
