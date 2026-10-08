package org.opensources.pokmaps.ui.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.data.settings.MapSettings
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

    private fun viewModel(games: FakeGameDao, maps: FakeMapDao = FakeMapDao()): MapViewModel {
        val dataStore = FakeDataStore()
        val gameRepository = GameRepository(games, GameSettings(dataStore))
        val mapRepository = MapRepository(maps)
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
    fun waitsForTheSelectedGame() {
        val viewModel = viewModel(FakeGameDao(games = emptyList()))
        val state = viewModel.state.value
        assertNull(state.mapState)
        assertNull(state.game)
        assertFalse(state.failed)
        viewModel.onAction(MapAction.Back)
        assertEquals(state, viewModel.state.value)
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
}
