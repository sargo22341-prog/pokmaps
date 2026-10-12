package org.opensources.pokmaps.ui.pokemon

import androidx.lifecycle.SavedStateHandle
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.AbilityRow
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakePokedexDao
import org.opensources.pokmaps.data.db.FakePokemonDao
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.data.db.StatRow
import org.opensources.pokmaps.data.db.TypeRow
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokemonUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class PokemonProfileValidationTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    @Test
    fun incompleteProfilesBecomeVisibleErrorsRatherThanPartialSheets() = runTest {
        val delegate = FakePokemonDao()
        val invalidProfiles = listOf(
            object : PokemonDao by delegate {
                override suspend fun number(pokemonId: Int, versionGroupId: Int): Int? = null
            },
            object : PokemonDao by delegate {
                override suspend fun types(pokemonId: Int, generationId: Int) = emptyList<TypeRow>()
            },
            object : PokemonDao by delegate {
                override suspend fun stats(pokemonId: Int, generationId: Int) = emptyList<StatRow>()
            },
            object : PokemonDao by delegate {
                override suspend fun stats(pokemonId: Int, generationId: Int) =
                    delegate.stats(pokemonId, generationId).map { it.copy(value = 0) }
            },
            object : PokemonDao by delegate {
                override suspend fun abilities(pokemonId: Int, generationId: Int, versionGroupId: Int) =
                    emptyList<AbilityRow>()
            }
        )
        for (dao in invalidProfiles) {
            val model = viewModel(dao, FakeGameDao.RUBY)
            val collector = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
            assertTrue(model.state.value.failed)
            assertFalse(model.state.value.loading)
            assertNull(model.state.value.details)
            collector.cancel()
        }
    }

    @Test
    fun aFutureSpeciesHasAnEmptyStateWithoutAnError() = runTest {
        val delegate = FakePokemonDao()
        val dao = object : PokemonDao by delegate {
            override suspend fun pokemon(pokemonId: Int) = delegate.pokemon(pokemonId)?.copy(generationId = 3)
        }
        val model = viewModel(dao, FakeGameDao.RED)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        assertFalse(model.state.value.failed)
        assertFalse(model.state.value.loading)
        assertNull(model.state.value.details)
    }

    private fun viewModel(dao: PokemonDao, game: Game): PokemonViewModel {
        val store = FakeDataStore()
        val games = GameRepository(FakeGameDao(listOf(game)), GameSettings(store))
        val collection = CollectionSettings(store)
        return PokemonViewModel(
            SavedStateHandle(mapOf(PokemonViewModel.POKEMON_ID to FakePokemonDao.PIKACHU)),
            ObservePokemonUseCase(games, PokemonRepository(dao, PokedexRepository(FakePokedexDao()))),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(games, collection),
            MapRequests()
        )
    }
}
