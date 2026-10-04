package org.opensources.pokmaps.ui.pokedex

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.opensources.pokmaps.data.db.EvolutionPairRow
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.data.db.PokedexRow
import org.opensources.pokmaps.data.db.PokemonMethodRow
import org.opensources.pokmaps.data.db.PokemonTypeRow
import org.opensources.pokmaps.data.db.TypeRow
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.pokedex.CaughtFilter
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokedexUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase

@OptIn(ExperimentalCoroutinesApi::class)
class PokedexViewModelTest {
    private val red = Game(1, "red", "Rouge", 1, "red-blue", 1)
    private val blue = Game(2, "blue", "Bleu", 1, "red-blue", 1)

    private lateinit var settings: GameSettings
    private lateinit var viewModel: PokedexViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        val dataStore = FakeDataStore()
        settings = GameSettings(dataStore)
        val collection = CollectionSettings(dataStore)
        val games = GameRepository(FakeGameDao(listOf(red, blue)), settings)
        viewModel = PokedexViewModel(
            ObservePokedexUseCase(games, PokedexRepository(FakePokedexDao())),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(collection)
        )
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun ids() = viewModel.state.value.entries.map { it.pokemonId }

    @Test
    fun loadsThePokedexOfTheSelectedGame() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertFalse(state.loading)
        assertEquals(red, state.game)
        assertEquals(listOf(23, 24, 27, 133, 134), ids())
        assertEquals(5, state.total)
        assertEquals(listOf("Normal", "Poison", "Sol", "Eau"), state.types.map { it.name })
        assertEquals(setOf(ObtainMethod.WALK), state.entries.first().obtainMethods)
    }

    @Test
    fun searchIgnoresAccents() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.search("evoli")
        assertEquals(listOf(133), ids())
        viewModel.search("134")
        assertEquals(listOf(134), ids())
    }

    @Test
    fun availabilityDependsOnTheVersion() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.toggleAvailableOnly()
        // Abo et Arbok en Rouge, Sabelette en Bleu ; Aquali évolue d'Évoli (don).
        assertEquals(listOf(23, 24, 133, 134), ids())
        settings.selectVersion(blue.versionId)
        assertEquals(blue, viewModel.state.value.game)
        assertEquals(listOf(27, 133, 134), ids())
    }

    @Test
    fun filtersByTypeAndMethodThenResets() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.search("a")
        viewModel.filterType(POISON)
        assertEquals(listOf(23, 24), ids())
        viewModel.filterType(null)
        viewModel.filterMethod(ObtainMethod.EVOLUTION)
        assertEquals(listOf(24, 134), ids())
        viewModel.resetFilters()
        assertNull(viewModel.state.value.filter.method)
        assertEquals("a", viewModel.state.value.filter.query)
    }

    @Test
    fun caughtPokemonAreTrackedPerVersionAndFavoritesAcrossGames() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val abo = viewModel.state.value.entries.first { it.pokemonId == 23 }
        viewModel.toggleCaught(abo)
        viewModel.toggleFavorite(abo)
        assertEquals(1, viewModel.state.value.caughtCount)
        viewModel.filterCaught(CaughtFilter.CAUGHT)
        assertEquals(listOf(23), ids())
        viewModel.filterCaught(CaughtFilter.MISSING)
        assertEquals(listOf(24, 27, 133, 134), ids())
        viewModel.filterCaught(CaughtFilter.ALL)
        viewModel.toggleFavoritesOnly()
        assertEquals(listOf(23), ids())
        // Bleu : rien de capturé dans cette version, mais les favoris sont communs à tous les jeux.
        settings.selectVersion(blue.versionId)
        assertEquals(0, viewModel.state.value.caughtCount)
        assertEquals(listOf(23), ids())
        assertFalse(viewModel.state.value.entries.single().caught)
        assertTrue(viewModel.state.value.entries.single().favorite)
    }

    private class FakeGameDao(private val games: List<Game>) : GameDao {
        override fun games(): Flow<List<Game>> = flowOf(games)
    }

    private class FakeDataStore : DataStore<Preferences> {
        private val state = MutableStateFlow(emptyPreferences())
        override val data: Flow<Preferences> = state

        override suspend fun updateData(transform: suspend (t: Preferences) -> Preferences): Preferences =
            transform(state.value).also { state.value = it }
    }

    private class FakePokedexDao : PokedexDao {
        override suspend fun pokedex(versionGroupId: Int) = listOf(
            PokedexRow(23, 23, "Abo", "Ekans"),
            PokedexRow(24, 24, "Arbok", "Arbok"),
            PokedexRow(27, 27, "Sabelette", "Sandshrew"),
            PokedexRow(133, 133, "Évoli", "Eevee"),
            PokedexRow(134, 134, "Aquali", "Vaporeon")
        )

        override suspend fun pokemonTypes(generationId: Int) = listOf(
            PokemonTypeRow(23, 1, POISON, "poison", "Poison"),
            PokemonTypeRow(24, 1, POISON, "poison", "Poison"),
            PokemonTypeRow(27, 1, 5, "ground", "Sol"),
            PokemonTypeRow(133, 1, 1, "normal", "Normal"),
            PokemonTypeRow(134, 1, 11, "water", "Eau")
        )

        override suspend fun types(generationId: Int) = listOf(
            TypeRow(1, "normal", "Normal"),
            TypeRow(POISON, "poison", "Poison"),
            TypeRow(5, "ground", "Sol"),
            TypeRow(11, "water", "Eau")
        )

        override suspend fun encounterMethods(versionId: Int) = when (versionId) {
            1 -> listOf(PokemonMethodRow(23, "walk"), PokemonMethodRow(133, "gift"))
            else -> listOf(PokemonMethodRow(27, "walk"), PokemonMethodRow(133, "gift"))
        }

        override suspend fun staticPokemon(versionGroupId: Int) = emptyList<PokemonMethodRow>()

        override suspend fun evolutions(versionGroupId: Int) =
            listOf(EvolutionPairRow(23, 24), EvolutionPairRow(133, 134))
    }

    private companion object {
        const val POISON = 4
    }
}
