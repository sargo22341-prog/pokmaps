package org.opensources.pokmaps.data.map

import android.content.res.AssetManager
import java.io.FileNotFoundException
import java.io.InputStream
import javax.inject.Inject
import org.opensources.pokmaps.domain.model.GameMap
import ovh.plrapps.mapcompose.core.TileStreamProvider

/** Fichiers embarqués dans les assets ; séparés de l'`AssetManager` pour que les tests JVM s'en passent. */
fun interface AssetFiles {
    /** Contenu du fichier, null s'il n'est pas embarqué. */
    fun open(path: String): InputStream?
}

/** Fichiers lus dans les assets de l'application. */
class AssetManagerFiles @Inject constructor(private val assets: AssetManager) : AssetFiles {
    override fun open(path: String): InputStream? = try {
        assets.open(path)
    } catch (_: FileNotFoundException) {
        null
    }
}

/** Tuiles des cartes, lues dans les assets. Les tuiles vides ne sont pas embarquées : rien n'est dessiné. */
class MapTiles @Inject constructor(private val files: AssetFiles) {
    fun provider(map: GameMap): TileStreamProvider =
        TileStreamProvider { row, column, level -> files.open(map.tilePath(level, row, column)) }

    /** Retouches de la version, par-dessus la carte ; null si la carte n'en a pas dans cette version. */
    fun versionProvider(map: GameMap): TileStreamProvider? = map.versionTilePath(0, 0, 0)?.let {
        TileStreamProvider { row, column, level -> map.versionTilePath(level, row, column)?.let(files::open) }
    }

    /** Mer répétée sous la carte, null si la carte n'en a pas. */
    fun seaProvider(map: GameMap): TileStreamProvider? = map.seaTilePath(0)?.let {
        TileStreamProvider { _, _, level -> map.seaTilePath(level)?.let(files::open) }
    }
}
