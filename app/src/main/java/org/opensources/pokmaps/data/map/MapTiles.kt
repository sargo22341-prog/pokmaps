package org.opensources.pokmaps.data.map

import android.content.res.AssetManager
import java.io.IOException
import javax.inject.Inject
import org.opensources.pokmaps.domain.model.GameMap
import ovh.plrapps.mapcompose.core.TileStreamProvider

/** Tuiles des cartes, lues dans les assets. Les tuiles vides ne sont pas embarquées : rien n'est dessiné. */
class MapTiles @Inject constructor(private val assets: AssetManager) {
    fun provider(map: GameMap): TileStreamProvider = TileStreamProvider { row, column, level ->
        try {
            assets.open(map.tilePath(level, row, column))
        } catch (_: IOException) {
            null
        }
    }
}
