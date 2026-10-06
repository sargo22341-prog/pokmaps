package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.Composable
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlin.math.min
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.ui.common.PixelArt
import ovh.plrapps.mapcompose.api.addMarker
import ovh.plrapps.mapcompose.api.addPath
import ovh.plrapps.mapcompose.api.removeAllMarkers
import ovh.plrapps.mapcompose.api.removePath
import ovh.plrapps.mapcompose.ui.state.MapState
import ovh.plrapps.mapcompose.ui.state.markers.model.RenderingStrategy

internal data class MapRenderState(
    val catalog: MapCatalog,
    val map: GameMap,
    val mapState: MapState,
    val layers: Set<MapLayer>,
    val animated: Boolean,
    val zone: MapInfo?,
    val wildMarkers: List<WildMarker>,
    val focusedObjectId: Int?,
    val highlightedPokemonId: Int?,
    val highlightedMaps: Set<Int>,
    val highlightedObjects: Set<Int>,
    val worldEntrances: Map<Int, MapWarp>,
    val objectScales: Map<Int, Float>
)

internal class MapOverlayRenderer {
    private val drawnPaths = mutableListOf<String>()

    fun render(state: MapRenderState) {
        state.mapState.removeAllMarkers()
        drawnPaths.forEach { state.mapState.removePath(it) }
        drawnPaths.clear()

        val zoneParts = zoneParts(state.catalog, state.zone)
        val entrances = state.catalog.entrancesOf(state.map.id)
        val objects = state.catalog.partsOf(state.map.id).flatMap { state.catalog.objects[it].orEmpty() }
        drawEntrances(state, zoneParts, entrances)
        drawObjects(state, zoneParts, objects)
        drawWildMarkers(state)
        drawFocusedObject(state)
        drawHighlight(state, entrances, objects)
    }

    private fun zoneParts(catalog: MapCatalog, zone: MapInfo?): Set<Int> = when {
        zone == null -> emptySet()
        zone.parentId == null -> catalog.partsOf(zone.id).toSet()
        else -> setOf(zone.id)
    }

    private fun drawEntrances(state: MapRenderState, zoneParts: Set<Int>, entrances: List<MapWarp>) {
        val zone = state.zone
        if (zone != null && zone.parentId != null) {
            drawRectangle(state, "${MapMarkerIds.ZONE_PATH}:${zone.id}", zone, ZONE_COLOR, 0f)
        }
        if (MapLayer.WARPS !in state.layers) return
        entrances.forEach { warp ->
            val always = warp.mapId in zoneParts
            drawMarker(state, "${MapMarkerIds.WARP}:${warp.id}", warp.x, warp.y, !always, 2f) {
                WarpMarker(state.mapState, alwaysVisible = always)
            }
        }
    }

    private fun drawObjects(state: MapRenderState, zoneParts: Set<Int>, objects: List<MapObject>) {
        objects.filter { MapLayer.of(it.kind) in state.layers }.forEach { obj ->
            val inZone = obj.mapId in zoneParts
            val pokemon = obj.kind == MapObjectKind.POKEMON && obj.pokemonId != null
            drawMarker(state, "${MapMarkerIds.OBJECT}:${obj.id}", obj.x, obj.y, !inZone, 1f, pokemon) {
                ObjectMarker(
                    state.mapState,
                    obj,
                    state.catalog.versionGroupIdentifier,
                    alwaysVisible = inZone,
                    scale = state.objectScales[obj.id] ?: 1f,
                    animated = state.animated
                )
            }
        }
    }

    private fun drawWildMarkers(state: MapRenderState) {
        if (MapLayer.WILD_POKEMON !in state.layers) return
        state.wildMarkers.forEachIndexed { index, wild ->
            drawMarker(
                state = state,
                id = "${MapMarkerIds.WILD}:${wild.pokemonId}:$index",
                x = wild.x,
                y = wild.y,
                lazy = false,
                zIndex = 1f,
                pokemon = true
            ) {
                WildPokemonMarker(state.mapState, wild, state.animated)
            }
        }
    }

    private fun drawFocusedObject(state: MapRenderState) {
        val focused = state.focusedObjectId?.let { state.catalog.objectsById[it] }
            ?.takeIf { it.mapId in state.catalog.partsOf(state.map.id) } ?: return
        drawMarker(
            state = state,
            id = "${MapMarkerIds.HIGHLIGHT_OBJECT}:${focused.id}",
            x = focused.x,
            y = focused.y,
            lazy = false,
            zIndex = 3f
        ) {
            HighlightMarker()
        }
    }

    private fun drawHighlight(state: MapRenderState, entrances: List<MapWarp>, objects: List<MapObject>) {
        val pokemonId = state.highlightedPokemonId ?: return
        state.catalog.partsOf(state.map.id)
            .filter { it in state.highlightedMaps }
            .mapNotNull { state.catalog.maps[it] }
            .forEach { drawRectangle(state, "${MapMarkerIds.HIGHLIGHT_PATH}:${it.id}", it, HIGHLIGHT_COLOR, 0.25f) }

        val highlightedEntrances = if (state.map.identifier == GameMap.WORLD) {
            state.highlightedMaps.mapNotNull { state.worldEntrances[it] }
        } else {
            entrances.filter { it.targetMapId in state.highlightedMaps }
        }
        highlightedEntrances.distinctBy { it.id }.forEach { warp ->
            drawMarker(state, "${MapMarkerIds.HIGHLIGHT_WARP}:${warp.id}", warp.x, warp.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }
        objects.filter {
            ((it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId) || it.id in state.highlightedObjects) &&
                it.id != state.focusedObjectId
        }.forEach { obj ->
            drawMarker(state, "${MapMarkerIds.HIGHLIGHT_OBJECT}:${obj.id}", obj.x, obj.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }
    }

    private fun drawMarker(
        state: MapRenderState,
        id: String,
        x: Int,
        y: Int,
        lazy: Boolean = true,
        zIndex: Float = 0f,
        pokemon: Boolean = false,
        content: @Composable () -> Unit
    ) {
        state.mapState.addMarker(
            id,
            x.toDouble() / state.map.width,
            y.toDouble() / state.map.height,
            relativeOffset = if (pokemon && !state.animated) POKEMON_OFFSET else CENTERED,
            zIndex = zIndex,
            clickableAreaScale = when {
                !pokemon -> FULL_CLICK_SCALE
                state.animated -> ANIMATED_CLICK_SCALE
                else -> POKEMON_CLICK_SCALE
            },
            clickableAreaCenterOffset = if (pokemon && !state.animated) POKEMON_CLICK_CENTER else NO_OFFSET,
            renderingStrategy =
                if (lazy) RenderingStrategy.LazyLoading(MapMarkerIds.LAZY_LOADER) else RenderingStrategy.Default,
            c = content
        )
    }

    private fun drawRectangle(state: MapRenderState, id: String, part: MapInfo, color: Color, fillAlpha: Float) {
        val whole = part.parentId == null
        val left = if (whole) 0.0 else part.x.toDouble() / state.map.width
        val top = if (whole) 0.0 else part.y.toDouble() / state.map.height
        val right = if (whole) 1.0 else min(1.0, (part.x + part.width).toDouble() / state.map.width)
        val bottom = if (whole) 1.0 else min(1.0, (part.y + part.height).toDouble() / state.map.height)
        state.mapState.addPath(id, width = 3.dp, color = color, fillColor = color.copy(alpha = fillAlpha)) {
            addPoints(listOf(left to top, right to top, right to bottom, left to bottom, left to top))
        }
        drawnPaths += id
    }

    private companion object {
        val CENTERED = Offset(-0.5f, -0.5f)
        val POKEMON_OFFSET = Offset(-0.5f, -PixelArt.POKEMON_CENTER_Y)
        val FULL_CLICK_SCALE = Offset(1f, 1f)
        val NO_OFFSET = Offset(0f, 0f)
        val POKEMON_CLICK_SCALE = Offset(PixelArt.POKEMON_CONTENT_WIDTH, 0.6f)
        val POKEMON_CLICK_CENTER = Offset(0f, PixelArt.POKEMON_CENTER_Y - 0.5f)
        val ANIMATED_CLICK_SCALE = Offset(0.6f, 0.6f)
        val ZONE_COLOR = Color(0xFFFFFFFF)
        val HIGHLIGHT_COLOR = Color(0xFFFFD600)
    }
}
