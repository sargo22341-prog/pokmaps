package org.opensources.pokmaps.ui.map

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.model.GameMap
import org.robolectric.RobolectricTestRunner
import org.robolectric.shadows.ShadowLooper
import ovh.plrapps.mapcompose.api.getMarkerInfo
import ovh.plrapps.mapcompose.api.markerDerivedState
import ovh.plrapps.mapcompose.ui.state.MapState

/** Le rendu incrémental des marqueurs aboutit toujours à ce que dessinerait une carte neuve. */
@RunWith(RobolectricTestRunner::class)
class MapOverlayRendererTest {
    private data class Drawn(val x: Double, val y: Double, val zIndex: Float)

    private val wildIds = listOf("${MapMarkerIds.WILD}:19:0", "${MapMarkerIds.WILD}:16:1")

    /** Tous les marqueurs, paresseux compris, lus dans l'état de MapCompose (et non dans ce qu'il affiche). */
    private fun drawn(state: MapState, ids: List<String>): Map<String, Drawn> = ids.mapNotNull { id ->
        state.getMarkerInfo(id)?.let { id to Drawn(it.x, it.y, it.zIndex) }
    }.toMap()

    private fun candidates(catalog: MapCatalog, map: GameMap): List<String> {
        val parts = catalog.partsOf(map.id)
        val objects = parts.flatMap { catalog.objects[it].orEmpty() }.map { it.id }
        val warps = parts.flatMap { catalog.warps[it].orEmpty() }.map { it.id }
        return objects.flatMap { listOf("${MapMarkerIds.OBJECT}:$it", "${MapMarkerIds.HIGHLIGHT_OBJECT}:$it") } +
            warps.flatMap { listOf("${MapMarkerIds.WARP}:$it", "${MapMarkerIds.HIGHLIGHT_WARP}:$it") } + wildIds
    }

    private fun newState(map: GameMap) = MapState(map.levelCount, map.width, map.height, GameMap.TILE_SIZE)

    private fun steps(catalog: MapCatalog, map: GameMap, state: MapState): List<MapRenderState> {
        val route = catalog.regionsOf(map.id).first { catalog.objects[it.id].orEmpty().size >= 2 }
        val wild = listOf(
            WildMarker(19, "Rattata", WildMethod.WALK, route.x + 8, route.y + 8),
            WildMarker(16, "Roucool", WildMethod.WALK, route.x + 24, route.y + 24)
        )
        val all = MapLayer.entries.toSet()
        val start = MapRenderState(catalog, map, state, all, false, null, MapOverlays(), null)
        val zone = start.copy(zone = route, overlays = MapOverlays(wildMarkers = wild))
        val withoutObjects = zone.copy(layers = setOf(MapLayer.WARPS, MapLayer.WILD_POKEMON))
        val highlighted = zone.copy(
            showConnections = true,
            highlightedPokemonId = 19,
            overlays = zone.overlays.copy(highlightedMaps = setOf(route.id))
        )
        return listOf(start, zone, withoutObjects, zone, highlighted, zone.copy(overlays = MapOverlays()), start)
    }

    /**
     * Ordre de ce que MapCompose affiche (marqueurs non paresseux) : les Pokémon sauvages après les objets.
     * Vrai si des objets et des Pokémon sauvages étaient affichés ensemble.
     */
    private fun assertWildDrawnLast(state: MapState): Boolean {
        ShadowLooper.idleMainLooper()
        val shown = state.markerDerivedState().value.map { it.id }
        val lastObject = shown.indexOfLast { it.startsWith("${MapMarkerIds.OBJECT}:") }
        val firstWild = shown.indexOfFirst { it.startsWith("${MapMarkerIds.WILD}:") }
        assertTrue(firstWild == -1 || lastObject < firstWild)
        return lastObject >= 0 && firstWild >= 0
    }

    @Test
    fun incrementalMarkersMatchAFreshRenderAfterEachChange() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.databaseBuilder(context, PokedexDatabase::class.java, "renderer-test.db")
            .createFromFile(File(requireNotNull(System.getProperty("pokemaps.database"))))
            .build()
        try {
            val game = database.gameDao().games().first().first()
            val catalog = MapRepository(database.mapDao(), Dispatchers.Unconfined).catalog(game)
            val map = checkNotNull(catalog.defaultWorld?.let { catalog.gameMap(it.id) })
            val ids = candidates(catalog, map)
            val state = newState(map)
            val renderer = MapOverlayRenderer()
            var orderChecks = 0
            for (step in steps(catalog, map, state)) {
                renderer.render(step)
                val fresh = newState(map)
                MapOverlayRenderer().render(step.copy(mapState = fresh))
                val expected = drawn(fresh, ids)
                assertTrue(expected.isNotEmpty())
                assertEquals(expected, drawn(state, ids))
                if (assertWildDrawnLast(state)) orderChecks++
                fresh.shutdown()
            }
            // Zone, retour des objets après leur masquage, surlignage : l'ordre a bien été contrôlé.
            assertEquals(3, orderChecks)
            state.shutdown()
        } finally {
            database.close()
        }
    }
}
