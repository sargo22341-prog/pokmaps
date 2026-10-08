package org.opensources.pokmaps.ui.map

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.usecase.GameMaps
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase

/** Lieu sélectionné et fiches de la carte, sans carte MapCompose affichée. */
@OptIn(ExperimentalCoroutinesApi::class)
class MapSelectionTest {
    private class Fixture(scope: CoroutineScope, details: FakeMapDao) {
        val session = MapSession(scope)
        val selection = MapSelection(
            session,
            GetMapEncountersUseCase(MapRepository(details)),
            GetMapObjectDetailsUseCase(MapRepository(details))
        )
    }

    /** Session avec le catalogue du petit monde ; `details` sert les rencontres et les fiches. */
    private suspend fun TestScope.fixture(
        details: FakeMapDao = FakeMapDao(),
        catalogData: FakeMapDao = FakeMapDao()
    ): Fixture {
        val catalog = MapRepository(catalogData).catalog(FakeGameDao.RED)
        return Fixture(CoroutineScope(UnconfinedTestDispatcher(testScheduler)), details).apply {
            session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        }
    }

    private fun Fixture.select(mapId: Int) = selection.selectZone(checkNotNull(session.catalog), mapId)

    private fun Fixture.useCompositePlan(empty: Boolean = false): MapCatalog {
        val original = checkNotNull(session.catalog)
        val route = original.maps.getValue(FakeMapDao.ROUTE_1)
        val room = original.maps.getValue(FakeMapDao.MART)
        val plan = room.copy(id = PLAN, identifier = "test-1f-plan", name = "Niveau", width = 512, height = 512)
        val catalog = original.copy(
            maps = original.maps + listOf(
                plan,
                route.copy(parentId = PLAN),
                room.copy(parentId = PLAN, x = 352, levelCount = 0)
            ).associateBy { it.id },
            areas = if (empty) {
                emptyMap()
            } else {
                original.areas +
                    (room.id to original.areas.getValue(route.id).map { it.copy(mapId = room.id) })
            }
        )
        session.setLoaded(GameMaps(FakeGameDao.RED, catalog))
        return catalog
    }

    @Test
    fun everyZoneOfTheFloorHasMarkersAndItsOwnPokemonDetails() = runTest {
        val fixture = fixture()
        fixture.useCompositePlan()
        fixture.select(PLAN)
        val markers = fixture.session.overlays.wildMarkers
        assertEquals(setOf(FakeMapDao.ROUTE_1, FakeMapDao.MART), markers.map { it.mapId }.toSet())
        assertEquals(1, checkNotNull(fixture.session.current.zone).encounters.size)
        fixture.selection.showWildPokemon(FakeMapDao.PIDGEY, FakeMapDao.MART)
        val detail = fixture.session.current.detail as MapDetail.WildPokemon
        assertEquals(1, detail.encounters.single().encounters.size)
    }

    @Test
    fun aCompositeWithoutEncountersRemainsEmpty() = runTest {
        val fixture = fixture()
        fixture.useCompositePlan(empty = true)
        fixture.select(PLAN)
        assertTrue(checkNotNull(fixture.session.current.zone).encounters.isEmpty())
        assertFalse(checkNotNull(fixture.session.current.zone).failed)
        assertTrue(fixture.session.overlays.wildMarkers.isEmpty())
    }

    @Test
    fun aCompositeWithUnreadableEncountersShowsAnError() = runTest {
        val fixture = fixture(FakeMapDao(encountersFailing = true))
        fixture.useCompositePlan()
        fixture.select(PLAN)
        assertTrue(checkNotNull(fixture.session.current.zone).failed)
        assertFalse(checkNotNull(fixture.session.current.zone).loading)
        assertTrue(fixture.session.overlays.wildMarkers.isEmpty())
    }

    @Test
    fun aRouteShowsItsWildPokemonOnTheMap() = runTest {
        val fixture = fixture()
        fixture.select(FakeMapDao.ROUTE_1)
        val zone = checkNotNull(fixture.session.current.zone)
        assertFalse(zone.loading)
        assertEquals(setOf(FakeMapDao.PIDGEY), zone.wildIds)
        assertEquals(listOf(FakeMapDao.PIDGEY), fixture.session.overlays.wildMarkers.map { it.pokemonId })
        fixture.selection.showWildPokemon(FakeMapDao.PIDGEY)
        assertEquals("Roucool", (fixture.session.current.detail as MapDetail.WildPokemon).name)
    }

    @Test
    fun timeFiltersUpdateBothTheListAndTheWildMarkers() = runTest {
        val fixture = fixture(details = FakeMapDao(timedEncounters = true))
        fixture.select(FakeMapDao.ROUTE_1)
        assertEquals(setOf(FakeMapDao.PIDGEY, 163), fixture.session.current.zone?.wildIds)
        fixture.selection.selectTime(TimeFilter.NIGHT)
        assertEquals(setOf(163), fixture.session.current.zone?.wildIds)
        assertEquals(setOf(163), fixture.session.overlays.wildMarkers.map { it.pokemonId }.toSet())
        fixture.selection.selectTime(TimeFilter.MORNING)
        assertTrue(checkNotNull(fixture.session.current.zone).encounters.isEmpty())
        assertFalse(checkNotNull(fixture.session.current.zone).failed)
        fixture.selection.selectTime(TimeFilter.DAY)
        assertEquals(setOf(FakeMapDao.PIDGEY), fixture.session.current.zone?.wildIds)
    }

    @Test
    fun aPlaceWithoutEncounterIsEmptyNotAnError() = runTest {
        val fixture = fixture()
        fixture.select(FakeMapDao.MART)
        val zone = checkNotNull(fixture.session.current.zone)
        assertTrue(zone.encounters.isEmpty())
        assertFalse(zone.failed)
        assertEquals(listOf("Jadielle"), zone.places.map { it.name })
    }

    @Test
    fun aZoneListsVisibleAndHiddenItems() = runTest {
        val fixture = fixture(catalogData = FakeMapDao(includeHiddenItem = true))
        fixture.select(FakeMapDao.ROUTE_1)
        val items = checkNotNull(fixture.session.current.zone).items
        assertEquals(listOf(FakeMapDao.ITEM, FakeMapDao.HIDDEN_ITEM), items.map { it.id })
        assertEquals(listOf("ITEM", "HIDDEN_ITEM"), items.map { it.kind.name })
    }

    @Test
    fun unreadableEncountersMarkTheZoneAsFailed() = runTest {
        val fixture = fixture(FakeMapDao(encountersFailing = true))
        fixture.select(FakeMapDao.ROUTE_1)
        val zone = checkNotNull(fixture.session.current.zone)
        assertTrue(zone.failed)
        assertFalse(zone.loading)
        assertTrue(fixture.session.overlays.wildMarkers.isEmpty())
    }

    @Test
    fun touchingObjectsOpensTheirDetail() = runTest {
        val fixture = fixture()
        val catalog = checkNotNull(fixture.session.catalog)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.CLERK]))
        val character = fixture.session.current.detail as MapDetail.Character
        assertFalse(character.loading)
        assertEquals(1, character.offers.size)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.ITEM]))
        val item = fixture.session.current.detail as MapDetail.Item
        assertEquals("Soigne 20 PV.", item.details?.description)
        fixture.selection.dismissDetail()
        assertNull(fixture.session.current.detail)
    }

    @Test
    fun touchingAFossilSaysWhatItBecomesAndAFacilityWhatItOffers() = runTest {
        val fixture = fixture()
        val catalog = checkNotNull(fixture.session.catalog)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.FOSSIL]))
        val fossil = fixture.session.current.detail as MapDetail.Character
        assertEquals("Kabuto", fossil.fossilUses.getValue("dome-fossil").pokemonName)
        assertEquals(listOf(CharacterRole.OBJECT, CharacterRole.GIFT), fossil.roles)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.PRIZES]))
        val prizes = fixture.session.current.detail as MapDetail.Character
        assertEquals(FakeMapDao.RED_ABRA_COINS, (prizes.offers.single() as NpcOffer.PrizePokemon).coins)
        assertEquals(listOf(CharacterRole.PRIZES), prizes.roles)
    }

    @Test
    fun unreadableDetailsAreAnError() = runTest {
        val fixture = fixture(FakeMapDao(failing = true))
        val catalog = checkNotNull(fixture.session.catalog)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.TRAINER]))
        val character = fixture.session.current.detail as MapDetail.Character
        assertTrue(character.failed)
        assertFalse(character.loading)
        fixture.selection.showObject(checkNotNull(catalog.objectsById[FakeMapDao.ITEM]))
        assertTrue((fixture.session.current.detail as MapDetail.Item).failed)
    }

    @Test
    fun clearingTheZoneRemovesItsPokemon() = runTest {
        val fixture = fixture()
        fixture.select(FakeMapDao.ROUTE_1)
        fixture.selection.clearZone()
        assertNull(fixture.session.current.zone)
        assertTrue(fixture.session.overlays.wildMarkers.isEmpty())
    }

    private companion object {
        const val PLAN = 1900
    }
}
