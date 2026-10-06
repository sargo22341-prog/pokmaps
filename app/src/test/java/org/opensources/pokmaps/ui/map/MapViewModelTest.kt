package org.opensources.pokmaps.ui.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.data.settings.MapSettings
import org.opensources.pokmaps.domain.usecase.DisplaySettingsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase
import org.opensources.pokmaps.domain.usecase.GetMapTilesUseCase
import org.opensources.pokmaps.domain.usecase.GetPokemonMapsUseCase
import org.opensources.pokmaps.domain.usecase.MapLayersUseCase
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObserveMapCatalogUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

/**
 * États de l'écran tant qu'aucune carte n'est affichée. Une carte MapCompose charge ses tuiles avec les API
 * graphiques d'Android, absentes des tests JVM : la sélection et les fiches sont testées dans [MapSelectionTest].
 */
class MapViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private fun viewModel(games: FakeGameDao, maps: FakeMapDao = FakeMapDao()): MapViewModel {
        val dataStore = FakeDataStore()
        val gameRepository = GameRepository(games, GameSettings(dataStore))
        val mapRepository = MapRepository(maps)
        return MapViewModel(
            ObserveMapCatalogUseCase(gameRepository, mapRepository),
            GetMapEncountersUseCase(mapRepository),
            GetPokemonMapsUseCase(mapRepository),
            GetMapObjectDetailsUseCase(mapRepository),
            MapRequests(),
            MapLayersUseCase(MapSettings(dataStore)),
            ObserveCollectionUseCase(gameRepository, CollectionSettings(dataStore)),
            DisplaySettingsUseCase(DisplaySettings(dataStore)),
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
    fun anUnreadableDatabaseIsAnError() {
        val state = viewModel(FakeGameDao(), FakeMapDao(failing = true)).state.value
        assertTrue(state.failed)
        assertNull(state.mapState)
        assertNull(state.zone)
    }
}
