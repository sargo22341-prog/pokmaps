package org.opensources.pokmaps.ui.map

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
import org.opensources.pokmaps.domain.map.WarpKind
import org.opensources.pokmaps.domain.model.GameMap
import ovh.plrapps.mapcompose.api.addLayer
import ovh.plrapps.mapcompose.api.addMarker
import ovh.plrapps.mapcompose.api.addPath
import ovh.plrapps.mapcompose.api.removeLayer
import ovh.plrapps.mapcompose.api.removeMarker
import ovh.plrapps.mapcompose.api.removePath
import ovh.plrapps.mapcompose.core.TileStreamProvider
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

internal class MapOverlayRenderer(private val tiles: (GameMap) -> TileStreamProvider) {
    private val drawnPaths = mutableListOf<String>()

    /** Marqueurs présents sur [drawnOn] ; une nouvelle carte MapCompose part vide. */
    private var drawnOn: MapState? = null
    private var drawn: Map<String, MarkerSpec> = emptyMap()

    /** Calque des tuiles de l'île superposée sur [drawnOn], null si elle n'est pas affichée. */
    private var islandLayer: String? = null

    fun render(state: MapRenderState) {
        drawnPaths.forEach { state.mapState.removePath(it) }
        drawnPaths.clear()
        if (drawnOn !== state.mapState) {
            drawnOn = state.mapState
            drawn = emptyMap()
            islandLayer = null
        }

        val wanted = LinkedHashMap<String, MarkerSpec>()
        val zoneParts = zoneParts(state.catalog, state.zone)
        val entrances = state.catalog.displayedEntrances(state.map.id, state.zone?.id)
        val objects = state.catalog.displayedObjects(state.map.id, state.zone?.id)
        syncIsland(state)
        drawConnections(state)
        drawEntrances(state, wanted, zoneParts, entrances)
        drawSecretBases(state, wanted, zoneParts)
        drawObjects(state, wanted, zoneParts, objects)
        drawWildMarkers(state, wanted)
        drawFocusedObject(state, wanted)
        drawFocusedWarp(state, wanted)
        drawHighlight(state, wanted, entrances, objects)
        drawRegionLabels(state, wanted)
        apply(state, wanted)
    }

    private fun drawRegionLabels(state: MapRenderState, wanted: MutableMap<String, MarkerSpec>) {
        if (state.map.identifier != "safari-atlas") return
        state.map.regions.forEach { region ->
            wanted.draw(
                "${MapMarkerIds.REGION}:${region.id}",
                MarkerSpec(region.x + 8, region.y + 8, false, 4f, false, MarkerContent.RegionLabel(region))
            )
        }
    }

    private fun apply(state: MapRenderState, wanted: Map<String, MarkerSpec>) {
        val updates = markerUpdates(drawn, wanted)
        updates.removed.forEach { state.mapState.removeMarker(it) }
        updates.added.forEach { id -> addMarker(state, id, wanted.getValue(id)) }
        drawn = wanted
    }

    /** L'île superposée apparaît sur la carte du monde tant qu'elle est le lieu sélectionné. */
    private fun syncIsland(state: MapRenderState) {
        val island = state.catalog.overlayIsland ?: return
        val shown = state.catalog.isIslandShown(state.map.id, state.zone?.id)
        val layer = islandLayer
        if (shown && layer == null) {
            val map = state.catalog.gameMap(island.islandId) ?: return
            islandLayer = state.mapState.addLayer(tiles(map))
        } else if (!shown && layer != null) {
            state.mapState.removeLayer(layer)
            islandLayer = null
        }
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

    private fun drawEntrances(
        state: MapRenderState,
        wanted: MutableMap<String, MarkerSpec>,
        zoneParts: Set<Int>,
        entrances: List<MapWarp>
    ) {
        val zone = state.zone
        if (zone != null && zone.parentId != null) {
            drawRectangle(state, "${MapMarkerIds.ZONE_PATH}:${zone.id}", zone, ZONE_COLOR, 0f)
        }
        if (MapLayer.WARPS !in state.layers) return
        entrances.forEach { warp ->
            val always = warp.mapId in zoneParts
            val index = state.catalog.connectionsOf(state.map.id).indexOfFirst { warp.id in it.warpIds }
            val content = if (warp.kind == WarpKind.MIRAGE) {
                val returning = warp.id == state.catalog.overlayIsland?.hide?.id
                val route = state.catalog.maps[warp.targetMapId]?.name.takeIf { returning }
                MarkerContent.MirageIsland(alwaysVisible = always || returning, returnTo = route)
            } else {
                MarkerContent.Warp(alwaysVisible = always || index >= 0, color = passageColor(index))
            }
            wanted.draw("${MapMarkerIds.WARP}:${warp.id}", MarkerSpec(warp.x, warp.y, !always, 2f, false, content))
        }
    }

    private fun drawSecretBases(state: MapRenderState, wanted: MutableMap<String, MarkerSpec>, zoneParts: Set<Int>) {
        if (MapLayer.SECRET_BASES !in state.layers) return
        state.catalog.secretBasesOf(state.map.id).forEach { base ->
            val warp = base.entrance
            val always = warp.mapId in zoneParts
            val content = MarkerContent.SecretBase(alwaysVisible = always)
            wanted.draw(
                "${MapMarkerIds.SECRET_BASE}:${warp.id}",
                MarkerSpec(warp.x, warp.y, !always, 2f, false, content)
            )
        }
    }

    private fun drawObjects(
        state: MapRenderState,
        wanted: MutableMap<String, MarkerSpec>,
        zoneParts: Set<Int>,
        objects: List<MapObject>
    ) {
        objects.filter { MapLayer.of(it) in state.layers }.forEach { obj ->
            val inZone = obj.mapId in zoneParts
            val pokemon = obj.kind == MapObjectKind.POKEMON && obj.pokemonId != null
            val position = state.catalog.markerPosition(obj)
            val content = MarkerContent.Element(
                obj,
                state.catalog.versionGroupIdentifier,
                alwaysVisible = inZone,
                scale = state.overlays.objectScales[obj.id] ?: 1f
            )
            val spec = MarkerSpec(position.x, position.y, !inZone, 1f, pokemon, content)
            wanted.draw("${MapMarkerIds.OBJECT}:${obj.id}", spec)
        }
        drawBattles(state, wanted, zoneParts, objects)
    }

    private fun drawBattles(
        state: MapRenderState,
        wanted: MutableMap<String, MarkerSpec>,
        zoneParts: Set<Int>,
        objects: List<MapObject>
    ) {
        val visible = objects.filter { MapLayer.of(it) in state.layers }.map { it.id }.toSet()
        for (battle in state.catalog.battleMarkers) {
            if (battle.objectId !in visible) continue
            val obj = state.catalog.objectsById.getValue(battle.objectId)
            val position = state.catalog.markerPosition(obj)
            val inZone = obj.mapId in zoneParts
            val spec = MarkerSpec(
                position.x + battle.x - obj.x,
                position.y + battle.y - obj.y,
                !inZone,
                2f,
                false,
                MarkerContent.Battle(inZone)
            )
            wanted.draw("${MapMarkerIds.OBJECT}:${obj.id}:battle", spec)
        }
    }

    private fun drawWildMarkers(state: MapRenderState, wanted: MutableMap<String, MarkerSpec>) {
        state.overlays.wildMarkers.forEachIndexed { index, wild ->
            val layer = if (wild.method == WildMethod.HONEY_TREE) MapLayer.HONEY_TREES else MapLayer.WILD_POKEMON
            if (layer !in state.layers) return@forEachIndexed
            val spec = MarkerSpec(wild.x, wild.y, lazy = false, zIndex = 1f, pokemon = true, MarkerContent.Wild(wild))
            wanted.draw("${MapMarkerIds.WILD}:${wild.pokemonId}:$index", spec)
        }
    }

    private fun drawFocusedObject(state: MapRenderState, wanted: MutableMap<String, MarkerSpec>) {
        val focused = state.overlays.focusedObjectId?.let { state.catalog.objectsById[it] }
            ?.takeIf { it.mapId in state.catalog.partsOf(state.map.id) } ?: return
        val position = state.catalog.markerPosition(focused)
        wanted.draw("${MapMarkerIds.HIGHLIGHT_OBJECT}:${focused.id}", highlight(position.x, position.y))
    }

    private fun drawFocusedWarp(state: MapRenderState, wanted: MutableMap<String, MarkerSpec>) {
        val id = state.overlays.focusedWarpId ?: return
        val parts = state.catalog.partsOf(state.map.id).toSet()
        val warp =
            parts.asSequence().flatMap { state.catalog.warps[it].orEmpty() }.firstOrNull { it.id == id } ?: return
        wanted.draw("${MapMarkerIds.HIGHLIGHT_WARP}:${warp.id}", highlight(warp.x, warp.y))
    }

    private fun drawHighlight(
        state: MapRenderState,
        wanted: MutableMap<String, MarkerSpec>,
        entrances: List<MapWarp>,
        objects: List<MapObject>
    ) {
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
            wanted.draw("${MapMarkerIds.HIGHLIGHT_WARP}:${warp.id}", highlight(warp.x, warp.y))
        }
        val overlays = state.overlays
        objects.filter {
            ((it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId) || it.id in overlays.highlightedObjects) &&
                it.id != overlays.focusedObjectId
        }.forEach { obj ->
            val position = state.catalog.markerPosition(obj)
            wanted.draw("${MapMarkerIds.HIGHLIGHT_OBJECT}:${obj.id}", highlight(position.x, position.y))
        }
    }

    private fun highlight(x: Int, y: Int) =
        MarkerSpec(x, y, lazy = false, zIndex = 3f, pokemon = false, content = MarkerContent.Highlight)

    /** Comme MapCompose, le premier marqueur d'un identifiant l'emporte. */
    private fun MutableMap<String, MarkerSpec>.draw(id: String, spec: MarkerSpec) {
        putIfAbsent(id, spec)
    }

    private fun addMarker(state: MapRenderState, id: String, spec: MarkerSpec) {
        state.mapState.addMarker(
            id,
            spec.x.toDouble() / state.map.width,
            spec.y.toDouble() / state.map.height,
            relativeOffset = if (spec.content is MarkerContent.RegionLabel) Offset.Zero else CENTERED,
            zIndex = spec.zIndex,
            // Le sprite d'un Pokémon est centré dans un cadre fait pour le plus grand : on touche son centre.
            clickableAreaScale = if (spec.pokemon) POKEMON_CLICK_SCALE else FULL_CLICK_SCALE,
            renderingStrategy =
                if (spec.lazy) RenderingStrategy.LazyLoading(MapMarkerIds.LAZY_LOADER) else RenderingStrategy.Default,
            c = { spec.content.Draw(state.mapState) }
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
