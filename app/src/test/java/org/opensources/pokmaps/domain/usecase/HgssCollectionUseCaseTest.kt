package org.opensources.pokmaps.domain.usecase

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.pokedex.CaptureScope
import org.opensources.pokmaps.domain.pokemon.PokemonFormTest

class HgssCollectionUseCaseTest {
    @Test
    fun capturesAndFormsStayPerCartridgeAndSharingIsExplicit() = runTest {
        val form = PokemonFormTest.form("normal", "Normale", List(6) { 50 })
        val heartgold = FakeGameDao.HEARTGOLD.copy(forms = mapOf(form.pokemonId to listOf(form)))
        val soulsilver = FakeGameDao.SOULSILVER.copy(forms = heartgold.forms)
        val catalog = listOf(FakeGameDao.GOLD, FakeGameDao.PLATINUM, heartgold, soulsilver)
        val store = FakeDataStore()
        val settings = CollectionSettings(store)
        val games = GameRepository(FakeGameDao(catalog), GameSettings(store))
        val update = UpdateCollectionUseCase(games, settings)
        val observe = ObserveCollectionUseCase(games, settings)
        update.setCaught(FakeGameDao.GOLD, 25, true)
        games.select(heartgold)
        assertTrue(observe().first().caught.isEmpty())
        update.setCaught(heartgold, 243, true)
        update.setFormCaught(heartgold, form.pokemonId, form.identifier, true)
        update.setFavorite(493, true)
        games.select(soulsilver)
        assertTrue(observe().first().caught.isEmpty())
        assertTrue(observe().first().forms.isEmpty())
        assertEquals(setOf(493), observe().first().favorites)
        settings.setCaptureScope(CaptureScope.GENERATION)
        assertEquals(setOf(243), observe().first().caught)
        assertEquals(setOf(form.identifier), observe().first().forms)
        settings.setCaptureScope(CaptureScope.ALL)
        assertEquals(setOf(25, 243), observe().first().caught)
        settings.setCaptureScope(CaptureScope.GAME)
        assertEquals(setOf(243), settings.caughtByVersion.first()[15])
        assertTrue(observe().first().caught.isEmpty())
    }
}
