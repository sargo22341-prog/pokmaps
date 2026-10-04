package org.opensources.pokmaps.ui.common

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.layout.ContentScale
import coil3.compose.AsyncImage
import org.opensources.pokmaps.domain.model.Sprites

/** Image des assets agrandie sans lissage, pour garder les pixels nets des sprites Game Boy. */
@Composable
fun AssetImage(
    path: String,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    alpha: Float = 1f,
    contentScale: ContentScale = ContentScale.Fit
) {
    AsyncImage(
        model = Sprites.assetUri(path),
        contentDescription = contentDescription,
        modifier = modifier,
        alpha = alpha,
        contentScale = contentScale,
        filterQuality = FilterQuality.None
    )
}
