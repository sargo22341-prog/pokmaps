package org.opensources.pokmaps.data.map

import android.graphics.BitmapFactory
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.opensources.pokmaps.domain.map.MapFrame
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.VersionGroup

/** L'aperçu de 256 pixels suffit à écarter les grandes marges transparentes des matrices DS. */
internal suspend fun mapTileFrame(files: AssetFiles, map: GameMap): MapFrame = withContext(Dispatchers.IO) {
    if (map.isWorld || map.versionGroupIdentifier !in DS_GROUPS) return@withContext MapFrame.FULL
    withTimeoutOrNull(READ_TIMEOUT_MS) {
        // Les tuiles absentes sont transparentes ; un fournisseur sans aperçu garde le cadre entier.
        val bytes = files.open(map.tilePath(0, 0, 0))?.use { it.readNBytes(MAX_TILE_BYTES + 1) }
            ?: return@withTimeoutOrNull MapFrame.FULL
        require(bytes.size <= MAX_TILE_BYTES) { "Tuile trop volumineuse : ${map.identifier}" }
        visibleFrame(bytes, map)
    } ?: throw IOException("Délai de lecture dépassé : ${map.identifier}")
}

private fun visibleFrame(bytes: ByteArray, map: GameMap): MapFrame {
    val dimensions = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, dimensions)
    require(dimensions.outWidth in 1..GameMap.TILE_SIZE && dimensions.outHeight in 1..GameMap.TILE_SIZE) {
        "Dimensions de tuile invalides : ${map.identifier}"
    }
    val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        ?: throw IOException("Tuile illisible : ${map.identifier}")
    try {
        val pixels = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        val occupied = pixels.indices.filter { pixels[it] ushr 24 != 0 }
        if (occupied.isEmpty()) return MapFrame.FULL
        val factor = Math.scalb(1.0, map.levelCount - 1)
        return MapFrame(
            (occupied.minOf { it % bitmap.width } * factor / map.width).coerceIn(0.0, 1.0),
            (occupied.minOf { it / bitmap.width } * factor / map.height).coerceIn(0.0, 1.0),
            ((occupied.maxOf { it % bitmap.width } + 1) * factor / map.width).coerceIn(0.0, 1.0),
            ((occupied.maxOf { it / bitmap.width } + 1) * factor / map.height).coerceIn(0.0, 1.0)
        )
    } finally {
        bitmap.recycle()
    }
}

private const val MAX_TILE_BYTES = 512 * 1024
private const val READ_TIMEOUT_MS = 3_000L
private val DS_GROUPS = setOf(VersionGroup.PLATINUM.identifier, VersionGroup.DIAMOND_PEARL.identifier)
