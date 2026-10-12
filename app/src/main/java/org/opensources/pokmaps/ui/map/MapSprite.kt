package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.IntSize
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.size.Size
import org.opensources.pokmaps.domain.model.Sprites

/** Un pixel du sprite pret occupe un pixel de carte, même pour les personnages GBA de 16 × 32 pixels. */
@Composable
internal fun MapSprite(path: String, contentDescription: String?, pixelScale: Float, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val request = remember(path, context) {
        ImageRequest.Builder(context).data(Sprites.assetUri(path)).size(Size.ORIGINAL).build()
    }
    var source by remember(path) { mutableStateOf(IntSize(16, 16)) }
    val size = with(LocalDensity.current) {
        DpSize((source.width * pixelScale).toDp(), (source.height * pixelScale).toDp())
    }
    AsyncImage(
        model = request,
        contentDescription = contentDescription,
        modifier = modifier.size(size),
        filterQuality = FilterQuality.None,
        onSuccess = { source = IntSize(it.result.image.width, it.result.image.height) }
    )
}
