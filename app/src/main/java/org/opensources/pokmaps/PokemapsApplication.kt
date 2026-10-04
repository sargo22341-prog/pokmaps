package org.opensources.pokmaps

import android.app.Application
import coil3.ImageLoader
import coil3.PlatformContext
import coil3.SingletonImageLoader
import coil3.gif.AnimatedImageDecoder
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class PokemapsApplication :
    Application(),
    SingletonImageLoader.Factory {
    /** Chargeur d'images de Coil, avec le décodeur des GIF animés (sprites animés des Pokémon). */
    override fun newImageLoader(context: PlatformContext): ImageLoader = ImageLoader.Builder(context)
        .components { add(AnimatedImageDecoder.Factory()) }
        .build()
}
