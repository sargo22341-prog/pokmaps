package org.opensources.pokmaps.ui.map

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.GeneratedGbaCatalog
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MapNavigationTest {
    @Test
    fun diveLevelsFollowTheSelectedRouteAndDisappearOnDeselect() = runTest {
        val repository = MapRepository(FakeMapDao())
        val catalog = GeneratedGbaCatalog.load("ruby-sapphire")
        val session = MapSession(backgroundScope)
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        val selection =
            MapSelection(session, GetMapEncountersUseCase(repository), GetMapObjectDetailsUseCase(repository))
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        navigation.selectWorld(checkNotNull(catalog.defaultWorld).id)
        assertTrue(session.current.floors.isEmpty())
        val route = checkNotNull(catalog.mapByIdentifier("route124"))
        navigation.open(route.id)
        val floors = session.current.floors
        assertEquals(2, floors.size)
        navigation.selectFloor(floors.last().mapId)
        assertEquals("hoenn-underwater", session.current.map?.identifier)
        assertEquals(floors.last().mapId, session.current.zone?.mapId)
        assertEquals(floors, session.current.floors)
        navigation.selectFloor(route.id)
        assertEquals("hoenn", session.current.map?.identifier)
        assertEquals(route.id, session.current.zone?.mapId)
        navigation.back()
        assertTrue(session.current.floors.isEmpty())
        navigation.open(checkNotNull(catalog.mapByIdentifier("route133")).id)
        assertTrue(session.current.floors.isEmpty())
        navigation.open(checkNotNull(catalog.mapByIdentifier("route134")).id)
        navigation.selectFloor(session.current.floors.last().mapId)
        assertEquals("underwater-route134", session.current.map?.identifier)
        assertEquals(2, session.current.floors.size)
        session.current.mapState?.shutdown()
    }

    @Test
    fun fruitLayerFollowsTheDisplayedMapContents() = runTest {
        val repository = MapRepository(FakeMapDao(includeFruitTree = true))
        val catalog = repository.catalog(FakeGameDao.RED)
        val session = MapSession(backgroundScope)
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        val selection = MapSelection(
            session,
            GetMapEncountersUseCase(repository),
            GetMapObjectDetailsUseCase(repository)
        )
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        navigation.show(checkNotNull(catalog.defaultWorld).id, null, null, null)
        assertTrue(session.current.hasFruitTrees)
        navigation.openPlace(MapPlace(FakeMapDao.MART, "Boutique"))
        assertFalse(session.current.hasFruitTrees)
        session.current.mapState?.shutdown()
    }

    @Test
    fun enteringAComposedRoomCentersTheWholeFloor() = runTest {
        val repository = MapRepository(FakeMapDao(includeCompositeInterior = true))
        val catalog = repository.catalog(FakeGameDao.RED)
        val session = MapSession(backgroundScope)
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        val selection =
            MapSelection(session, GetMapEncountersUseCase(repository), GetMapObjectDetailsUseCase(repository))
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        navigation.openPlace(MapPlace(FakeMapDao.MART, "Boutique", 224, 112))
        assertEquals(FakeMapDao.PLAN, session.current.map?.id)
        val position = checkNotNull(navigation.currentPosition())
        assertEquals(0.5, position.x, 0.0001)
        assertEquals(0.5, position.y, 0.0001)
        assertEquals(FakeMapDao.MART, session.current.zone?.mapId)
        session.current.mapState?.shutdown()
    }

    @Test
    fun aRecreatedViewKeepsItsRequestedCenterBeforeLayout() = runTest {
        val repository = MapRepository(FakeMapDao())
        val catalog = repository.catalog(FakeGameDao.RED)
        val session = MapSession(backgroundScope)
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        val selection = MapSelection(
            session,
            GetMapEncountersUseCase(repository),
            GetMapObjectDetailsUseCase(repository)
        )
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        val world = checkNotNull(catalog.defaultWorld)
        navigation.show(world.id, 0.62, 0.73, 4.0)
        val before = checkNotNull(navigation.currentPosition())
        assertEquals(0.62, before.x, 0.0001)
        assertEquals(0.73, before.y, 0.0001)
        navigation.show(world.id, before.x, before.y, before.scale)
        val recreated = checkNotNull(navigation.currentPosition())
        assertEquals(before, recreated)
        navigation.stay(catalog, recreated, false)
        assertEquals(before, navigation.currentPosition())
        session.current.mapState?.shutdown()
    }

    @Test
    fun aNewWorldStartsAtItsStartingTownBeforeLayout() = runTest {
        val repository = MapRepository(FakeMapDao())
        val original = repository.catalog(FakeGameDao.RED)
        val worldInfo = checkNotNull(original.defaultWorld)
        val catalog = original.copy(
            maps = original.maps + (worldInfo.id to worldInfo.copy(startMapId = FakeMapDao.ROUTE_1))
        )
        val session = MapSession(backgroundScope)
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        val selection = MapSelection(
            session,
            GetMapEncountersUseCase(repository),
            GetMapObjectDetailsUseCase(repository)
        )
        val navigation = MapNavigation(session, selection, GetMapTilesUseCase(MapTiles { null }))
        val world = checkNotNull(catalog.defaultWorld)
        navigation.show(world.id, 0.1, 0.1, 4.0)
        navigation.selectWorld(world.id)
        val map = checkNotNull(session.current.map)
        val start = map.regions.first { it.id == map.startRegionId }
        val position = checkNotNull(navigation.currentPosition())
        assertEquals(start.centerX.toDouble() / map.width, position.x, 0.0001)
        assertEquals(start.centerY.toDouble() / map.height, position.y, 0.0001)
        session.current.mapState?.shutdown()
    }
}
