package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.AssetImage
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.ui.state.MapState

/** Les marqueurs des calques ne s'affichent qu'à partir d'un certain zoom, pour ne pas surcharger la carte. */
@Composable
private fun visibleAtScale(mapState: MapState): Boolean {
    val visible by remember(mapState) { derivedStateOf { mapState.scale >= MIN_MARKER_SCALE } }
    return visible
}

/** Entrée (porte, escalier, grotte) : on la touche pour entrer. */
@Composable
fun WarpMarker(mapState: MapState) {
    if (!visibleAtScale(mapState)) return
    Box(
        Modifier
            .size(14.dp)
            .background(WARP_COLOR.copy(alpha = 0.85f), CircleShape)
            .border(2.dp, Color.White, CircleShape)
    )
}

/** Objet, objet caché, dresseur ou Pokémon fixe, dessiné avec son sprite du jeu. */
@Composable
fun ObjectMarker(mapState: MapState, obj: MapObject, versionGroupIdentifier: String) {
    if (!visibleAtScale(mapState)) return
    val sprite = obj.sprite
    val itemIdentifier = obj.itemIdentifier
    when {
        obj.kind == MapObjectKind.HIDDEN_ITEM && itemIdentifier != null -> Box(
            Modifier
                .size(22.dp)
                .background(Color.Black.copy(alpha = 0.35f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            AssetImage(
                Sprites.item(itemIdentifier),
                contentDescription = null,
                alpha = 0.8f,
                modifier = Modifier.size(20.dp)
            )
        }

        sprite != null -> AssetImage(
            Sprites.mapSprite(versionGroupIdentifier, sprite),
            contentDescription = null,
            modifier = Modifier.size(24.dp)
        )

        else -> Box(Modifier.size(12.dp).background(Color.White, CircleShape))
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
private const val MIN_MARKER_SCALE = 1.0
