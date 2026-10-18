package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import org.robolectric.RobolectricTestRunner
import ovh.plrapps.mapcompose.api.centroidX
import ovh.plrapps.mapcompose.api.centroidY
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.ui.MapUI

@RunWith(RobolectricTestRunner::class)
class MapInteriorFramingTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun interiorIsCenteredAndFittedAfterTheViewportIsMeasured() {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        val interior = MapInfo(1, "interior", "Bâtiment", null, 0, 0, 512, 768, 3)
        val catalog = MapCatalog("platinum", mapOf(1 to interior), emptyMap(), emptyMap(), emptyMap())
        val repository = MapRepository(FakeMapDao(), Dispatchers.Unconfined)
        val session = MapSession(scope, noTiles)
        session.setLoaded(GameMaps(FakeGameDao.PLATINUM, catalog))
        val selection =
            MapSelection(session, GetMapEncountersUseCase(repository), GetMapObjectDetailsUseCase(repository))
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        try {
            compose.runOnIdle { navigation.show(1, null, null, null) }
            val state = checkNotNull(session.current.mapState)
            compose.setContent { MapUI(Modifier.size(300.dp, 500.dp), state = state) }
            compose.waitUntil(timeoutMillis = 5_000) { state.scale < 3.9 }
            compose.runOnIdle {
                assertEquals(0.5, state.centroidX, 0.02)
                assertEquals(0.5, state.centroidY, 0.02)
                assertTrue(state.scale in 0.5..2.0)
            }
        } finally {
            session.current.mapState?.shutdown()
            scope.cancel()
        }
    }
}
