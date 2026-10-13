package org.opensources.pokmaps.ui.map

import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.emptyFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.data.settings.MapSettings
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import org.opensources.pokmaps.domain.usecase.GetPokemonMapsUseCase
import org.opensources.pokmaps.domain.usecase.MapLayersUseCase
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObserveMapCatalogUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule
import org.robolectric.RobolectricTestRunner

/**
 * Chargement de la carte et demandes des autres écrans. Robolectric fournit les API graphiques d'Android dont
 * MapCompose a besoin ; la sélection et les fiches sont testées dans [MapSelectionTest].
 */
@RunWith(RobolectricTestRunner::class)
class MapViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()

    private fun viewModel(
        games: GameDao,
        maps: FakeMapDao = FakeMapDao(),
        dataStore: FakeDataStore = FakeDataStore()
    ): MapViewModel {
        val gameRepository = GameRepository(games, GameSettings(dataStore))
        val mapRepository = MapRepository(maps, Dispatchers.Unconfined)
        return MapViewModel(
            ObserveMapCatalogUseCase(gameRepository, mapRepository),
            GetMapEncountersUseCase(mapRepository),
            GetPokemonMapsUseCase(mapRepository),
            GetMapObjectDetailsUseCase(mapRepository),
            requests,
            MapLayersUseCase(MapSettings(dataStore)),
            ObserveCollectionUseCase(gameRepository, CollectionSettings(dataStore)),
            GetMapTilesUseCase(MapTiles { null })
        )
    }

    @Test
    fun connectionLinesAreInitiallyHiddenAndCanBeToggled() {
        val model = viewModel(FakeGameDao())
        model.onScreenShown()
        assertFalse(model.state.value.showConnections)
        model.onAction(MapAction.ToggleConnections)
        assertTrue(model.state.value.showConnections)
        model.onAction(MapAction.ToggleConnections)
        assertFalse(model.state.value.showConnections)
    }

    @Test
    fun aHiddenMapAppliesTheLatestGameBeforeItsPendingRequest() {
        val dataStore = FakeDataStore()
        val viewModel = viewModel(FakeGameDao(), dataStore = dataStore)
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(FakeGameDao.BLUE.versionId) }
        requests.send(MapRequest.OpenPlace("viridian-mart"))
        viewModel.onScreenShown()
        assertEquals(FakeGameDao.BLUE, viewModel.state.value.game)
        assertEquals("viridian-mart", viewModel.state.value.map?.identifier)
        assertNull(requests.pending.value)
    }

    @Test
    fun waitsForTheSelectedGame() {
        val pending = object : GameDao {
            override fun games() = emptyFlow<List<org.opensources.pokmaps.domain.model.Game>>()
        }
        val viewModel = viewModel(pending)
        val state = viewModel.state.value
        assertNull(state.mapState)
        assertNull(state.game)
        assertFalse(state.failed)
        viewModel.onAction(MapAction.Back)
        assertEquals(state, viewModel.state.value)
    }

    @Test
    fun anEmptyGameCatalogIsAnError() {
        val state = viewModel(FakeGameDao(games = emptyList())).state.value
        assertTrue(state.failed)
        assertNull(state.mapState)
    }

    @Test
    fun aCorruptCollectionKeepsItsPreviousValuesAndReportsFailure() {
        val store = FakeDataStore()
        val collection = CollectionSettings(store)
        kotlinx.coroutines.test.runTest { collection.setCaught(setOf(1), 25, true) }
        val model = viewModel(FakeGameDao(), dataStore = store)
        model.onScreenShown()
        assertEquals(setOf(25), model.state.value.caught)
        kotlinx.coroutines.test.runTest {
            store.edit { it[stringSetPreferencesKey("favorite_pokemon")] = setOf("invalid") }
        }
        assertEquals(setOf(25), model.state.value.caught)
        assertEquals(MapMessage.CollectionFailed, model.state.value.message)
        assertFalse(model.state.value.failed)
        model.onAction(MapAction.MessageShown)
        assertNull(model.state.value.message)
    }

    @Test
    fun aGameWithoutMapsIsEmptyNotAnError() {
        val viewModel = viewModel(FakeGameDao(), FakeMapDao(emptyMaps = true))
        viewModel.onScreenShown()
        assertEquals(FakeGameDao.RED, viewModel.state.value.game)
        assertNull(viewModel.state.value.map)
        assertFalse(viewModel.state.value.failed)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() {
        val state = viewModel(FakeGameDao(), FakeMapDao(failing = true)).state.value
        assertTrue(state.failed)
        assertNull(state.mapState)
        assertNull(state.zone)
    }

    @Test
    fun theMapIsCreatedOnceTheScreenIsShown() {
        val viewModel = viewModel(FakeGameDao())
        assertNull(viewModel.state.value.map)

        viewModel.onScreenShown()
        assertEquals("kanto", viewModel.state.value.map?.identifier)
    }

    @Test
    fun aRequestSentWhileTheMapIsHiddenWaitsForTheScreen() {
        val viewModel = viewModel(FakeGameDao())
        viewModel.onScreenShown()
        viewModel.onScreenHidden()

        // « Voir sur la carte » depuis une fiche : traitée tout de suite, la carte serait recréée au retour de
        // l'écran à son ancienne position, et le recentrage perdu.
        val request = MapRequest.OpenPlace("viridian-mart")
        requests.send(request)
        assertEquals("kanto", viewModel.state.value.map?.identifier)
        assertEquals(request, requests.pending.value)

        viewModel.onScreenShown()
        assertEquals("viridian-mart", viewModel.state.value.map?.identifier)
        assertNull(requests.pending.value)
    }

    @Test
    fun changingGen3BranchResetsPlaceTimeAndHighlight() {
        val dataStore = FakeDataStore()
        val games = FakeGameDao(listOf(FakeGameDao.EMERALD, FakeGameDao.FIRERED))
        val model = viewModel(games, dataStore = dataStore)
        model.onScreenShown()
        requests.send(MapRequest.OpenPlace("viridian-mart"))
        requests.send(MapRequest.HighlightPokemon(FakeMapDao.PIDGEY, "Roucool"))
        model.onAction(MapAction.CycleTime)
        assertEquals(FakeGameDao.EMERALD, model.state.value.game)
        assertEquals(FakeMapDao.PIDGEY, model.state.value.highlight?.pokemonId)
        val previousMap = model.state.value.mapState
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(FakeGameDao.FIRERED.versionId) }
        assertEquals(FakeGameDao.FIRERED, model.state.value.game)
        assertNotSame(previousMap, model.state.value.mapState)
        assertEquals("kanto", model.state.value.map?.identifier)
        assertEquals(TimeFilter.ALL, model.state.value.time)
        assertNull(model.state.value.highlight)
        assertNull(model.state.value.zone)
    }

    @Test
    fun aSharedFamilyPreservesSelectedZoneAndAvailableTimeFilter() {
        val dataStore = FakeDataStore()
        val gold = FakeGameDao.GOLD.copy(hasTimeOfDay = true)
        val crystal = gold.copy(versionId = 6, versionGroupId = 4, versionGroupIdentifier = "crystal")
        val model = viewModel(FakeGameDao(listOf(gold, crystal)), dataStore = dataStore)
        model.onScreenShown()
        model.onAction(MapAction.OpenPlace(MapPlace(FakeMapDao.ROUTE_1, "Route 1")))
        model.onAction(MapAction.CycleTime)
        assertEquals(FakeMapDao.ROUTE_1, model.state.value.zone?.mapId)
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(crystal.versionId) }
        assertEquals(FakeMapDao.ROUTE_1, model.state.value.zone?.mapId)
        assertEquals(TimeFilter.MORNING, model.state.value.time)
        assertFalse(model.state.value.failed)
    }

    @Test
    fun hoennVersionsPreservePlaceAndHighlight() {
        val dataStore = FakeDataStore()
        val games = FakeGameDao(listOf(FakeGameDao.EMERALD, FakeGameDao.RUBY))
        val model = viewModel(games, dataStore = dataStore)
        model.onScreenShown()
        requests.send(MapRequest.OpenPlace("viridian-mart"))
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(FakeGameDao.RUBY.versionId) }
        assertEquals("viridian-mart", model.state.value.map?.identifier)
        requests.send(MapRequest.HighlightPokemon(FakeMapDao.PIDGEY, "Roucool"))
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(FakeGameDao.EMERALD.versionId) }
        assertEquals(FakeMapDao.PIDGEY, model.state.value.highlight?.pokemonId)
    }

    @Test
    fun changingGenerationResetsTheWorldAndClearsTimeAndHighlight() {
        val dataStore = FakeDataStore()
        val games = FakeGameDao(listOf(FakeGameDao.RED, FakeGameDao.GOLD))
        val viewModel = viewModel(games, dataStore = dataStore)
        viewModel.onScreenShown()
        viewModel.onAction(MapAction.CycleTime)
        requests.send(MapRequest.HighlightPokemon(FakeMapDao.PIDGEY, "Roucool"))
        assertEquals(TimeFilter.MORNING, viewModel.state.value.time)
        val previousMap = viewModel.state.value.mapState
        kotlinx.coroutines.test.runTest { GameSettings(dataStore).selectVersion(FakeGameDao.GOLD.versionId) }
        assertEquals(FakeGameDao.GOLD, viewModel.state.value.game)
        assertEquals(TimeFilter.ALL, viewModel.state.value.time)
        assertNull(viewModel.state.value.highlight)
        assertNotSame(previousMap, viewModel.state.value.mapState)
    }
}
