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
    val showConnections: Boolean,
    val zone: MapInfo?,
    val overlays: MapOverlays,
    val highlightedPokemonId: Int?
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
        drawConnections(state)
        drawEntrances(state, zoneParts, entrances)
        drawObjects(state, zoneParts, objects)
        drawWildMarkers(state)
        drawFocusedObject(state)
        drawHighlight(state, entrances, objects)
    }

    private fun zoneParts(catalog: MapCatalog, zone: MapInfo?): Set<Int> = when {
        zone == null -> emptySet()
        catalog.displayedMapOf(zone.id)?.isWorld == false -> catalog.partsOf(zone.parentId ?: zone.id).toSet()
        zone.parentId == null -> catalog.partsOf(zone.id).toSet()
        else -> setOf(zone.id)
    }

    private fun drawConnections(state: MapRenderState) {
        if (MapLayer.WARPS !in state.layers || !state.showConnections) return
        state.catalog.connectionsOf(state.map.id).forEachIndexed { index, connection ->
            val id = "connection:${connection.warpId}"
            state.mapState.addPath(id, width = 2.dp, color = passageColor(index)) {
                addPoints(
                    listOf(
                        connection.x.toDouble() / state.map.width to connection.y.toDouble() / state.map.height,
                        (connection.targetX.toDouble() / state.map.width) to
                            (connection.targetY.toDouble() / state.map.height)
                    )
                )
            }
            drawnPaths += id
        }
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
                val index = state.catalog.connectionsOf(state.map.id).indexOfFirst { warp.id in it.warpIds }
                WarpMarker(state.mapState, alwaysVisible = always || index >= 0, color = passageColor(index))
            }
        }
    }

    private fun drawObjects(state: MapRenderState, zoneParts: Set<Int>, objects: List<MapObject>) {
        objects.filter { MapLayer.of(it) in state.layers }.forEach { obj ->
            val inZone = obj.mapId in zoneParts
            val pokemon = obj.kind == MapObjectKind.POKEMON && obj.pokemonId != null
            val position = state.catalog.markerPosition(obj)
            drawMarker(state, "${MapMarkerIds.OBJECT}:${obj.id}", position.x, position.y, !inZone, 1f, pokemon) {
                ObjectMarker(
                    state.mapState,
                    obj,
                    state.catalog.versionGroupIdentifier,
                    alwaysVisible = inZone,
                    scale = state.overlays.objectScales[obj.id] ?: 1f
                )
            }
        }
    }

    private fun drawWildMarkers(state: MapRenderState) {
        if (MapLayer.WILD_POKEMON !in state.layers) return
        state.overlays.wildMarkers.forEachIndexed { index, wild ->
            drawMarker(
                state = state,
                id = "${MapMarkerIds.WILD}:${wild.pokemonId}:$index",
                x = wild.x,
                y = wild.y,
                lazy = false,
                zIndex = 1f,
                pokemon = true
            ) {
                WildPokemonMarker(state.mapState, wild)
            }
        }
    }

    private fun drawFocusedObject(state: MapRenderState) {
        val focused = state.overlays.focusedObjectId?.let { state.catalog.objectsById[it] }
            ?.takeIf { it.mapId in state.catalog.partsOf(state.map.id) } ?: return
        val position = state.catalog.markerPosition(focused)
        drawMarker(
            state = state,
            id = "${MapMarkerIds.HIGHLIGHT_OBJECT}:${focused.id}",
            x = position.x,
            y = position.y,
            lazy = false,
            zIndex = 3f
        ) {
            HighlightMarker()
        }
    }

    private fun drawHighlight(state: MapRenderState, entrances: List<MapWarp>, objects: List<MapObject>) {
        val pokemonId = state.highlightedPokemonId ?: return
        state.catalog.partsOf(state.map.id)
            .filter { it in state.overlays.highlightedMaps }
            .mapNotNull { state.catalog.maps[it] }
            .forEach { drawRectangle(state, "${MapMarkerIds.HIGHLIGHT_PATH}:${it.id}", it, HIGHLIGHT_COLOR, 0.25f) }

        state.overlays.highlightedMaps.filter { it !in state.overlays.worldEntrances }
            .mapNotNull { state.catalog.maps[it]?.originMapId }
            .distinct().mapNotNull { state.catalog.maps[it] }
            .filter { it.parentId == state.map.id }
            .forEach { drawRectangle(state, "${MapMarkerIds.HIGHLIGHT_PATH}:${it.id}", it, HIGHLIGHT_COLOR, 0.25f) }

        val highlightedEntrances = if (state.map.isWorld) {
            state.overlays.highlightedMaps.filter { state.catalog.worldOf(it)?.id == state.map.id }
                .mapNotNull { state.overlays.worldEntrances[it] }
        } else {
            entrances.filter { it.targetMapId in state.overlays.highlightedMaps }
        }
        highlightedEntrances.distinctBy { it.id }.forEach { warp ->
            drawMarker(state, "${MapMarkerIds.HIGHLIGHT_WARP}:${warp.id}", warp.x, warp.y, lazy = false, zIndex = 3f) {
                HighlightMarker()
            }
        }
        val overlays = state.overlays
        objects.filter {
            ((it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId) || it.id in overlays.highlightedObjects) &&
                it.id != overlays.focusedObjectId
        }.forEach { obj ->
            val position = state.catalog.markerPosition(obj)
            val id = "${MapMarkerIds.HIGHLIGHT_OBJECT}:${obj.id}"
            drawMarker(state, id, position.x, position.y, lazy = false, zIndex = 3f) {
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
            relativeOffset = CENTERED,
            zIndex = zIndex,
            // Le sprite d'un Pokémon est centré dans un cadre fait pour le plus grand : on touche son centre.
            clickableAreaScale = if (pokemon) POKEMON_CLICK_SCALE else FULL_CLICK_SCALE,
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
        val FULL_CLICK_SCALE = Offset(1f, 1f)
        val POKEMON_CLICK_SCALE = Offset(0.6f, 0.6f)
        val ZONE_COLOR = Color(0xFFFFFFFF)
        val HIGHLIGHT_COLOR = Color(0xFFFFD600)
    }
}
