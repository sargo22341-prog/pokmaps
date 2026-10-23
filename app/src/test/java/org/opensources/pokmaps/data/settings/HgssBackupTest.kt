package org.opensources.pokmaps.data.settings

import android.content.Context
import android.net.Uri
import androidx.test.core.app.ApplicationProvider
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.opensources.pokmaps.domain.usecase.CollectionBackupUseCase
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf

@RunWith(RobolectricTestRunner::class)
class HgssBackupTest {
    private val form = org.opensources.pokmaps.domain.pokemon.PokemonFormTest.form("normal", "Normale", List(6) { 50 })
    private val games = listOf(
        FakeGameDao.GOLD,
        FakeGameDao.PLATINUM,
        FakeGameDao.HEARTGOLD.copy(forms = mapOf(form.pokemonId to listOf(form))),
        FakeGameDao.SOULSILVER.copy(forms = mapOf(form.pokemonId to listOf(form)))
    )
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val address = Uri.parse("content://collection/hgss")

    @Test
    fun manualObservationsRemainIndependentAndCanBeRemoved() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(games))
        settings.observeRoamer(15, 243, "route-29")
        settings.observeRoamer(16, 243, "route-46")
        assertEquals(mapOf(243 to "route-29"), settings.progress(15).first().roamerObservations)
        assertEquals(mapOf(243 to "route-46"), settings.progress(16).first().roamerObservations)
        settings.observeRoamer(15, 243, null)
        assertTrue(settings.progress(15).first().roamerObservations.isEmpty())
        assertEquals(mapOf(243 to "route-46"), settings.progress(16).first().roamerObservations)
    }

    @Test
    fun commonExportPreservesEachCartridgeAndHistoricalSinnohKey() {
        val backup = collection()
        val encoded = BackupJson.encode(backup)
        assertEquals(backup, BackupJson.decode(encoded, games))
        val json = JSONObject(encoded).getJSONArray("games")
        val sinnoh = (0 until json.length()).map { json.getJSONObject(it) }.single { it.getInt("version") == 14 }
        assertTrue(sinnoh.has("sinnohRoamers"))
        val hgss = (0 until json.length()).map { json.getJSONObject(it) }.single { it.getInt("version") == 15 }
        assertTrue(hgss.has("roamerObservations"))
    }

    @Test
    fun oldSchemaOneMergesThroughUseCaseWithoutLosingProgress() = runTest {
        val store = FakeDataStore()
        val tools = CollectionBackupUseCase(CollectionBackupRepository(context, store, FakeGameDao(games)))
        import(tools, BackupJson.encode(collection()))
        import(
            tools,
            """{"format":"pokmaps-collection","schema":1,"favorites":[25],"games":[
            {"version":4,"caught":[25],"completed":["johto-start"],"roamers":[]}
        ]}"""
        )
        val output = ByteArrayOutputStream()
        shadowOf(context.contentResolver).registerOutputStream(address, output)
        tools.export(address.toString())
        val restored = BackupJson.decode(output.toString(Charsets.UTF_8), games)
        assertEquals(setOf(25, 493), restored.favorites)
        assertEquals(setOf(25), restored.caught[4])
        for (version in 14..16) {
            assertEquals(collection().caught[version], restored.caught[version])
            assertEquals(collection().guides[version], restored.guides[version])
        }
        assertEquals(collection().unown, restored.unown.filterValues { it.isNotEmpty() })
        assertEquals(collection().forms, restored.forms.filterValues { it.isNotEmpty() })
        val before = store.data.first()
        val invalid = BackupJson.encode(collection()).replace("route-29", "route-201")
        try {
            import(tools, invalid)
            throw AssertionError("Route incompatible acceptee")
        } catch (_: IllegalArgumentException) {
            assertEquals(before, store.data.first())
        }
    }

    @Test
    fun foreignSpeciesFormsVersionsAndWrongCartridgeRoamersAreRejected() {
        val text = BackupJson.encode(collection())
        val forms = JSONObject(text)
        forms.getJSONArray("games").getJSONObject(1).put("forms", org.json.JSONArray(listOf("unknown-form")))
        assertThrows(IllegalArgumentException::class.java) { BackupJson.decode(forms.toString(), games) }
        for (invalid in listOf(
            text.replace("route-29", "route-201"),
            text.replace("route-1", "route-29"),
            text.replace("493", "494"),
            text.replace("\"version\": 15", "\"version\": 17"),
            text.replace("\"380\"", "\"381\"")
        )) {
            assertThrows(IllegalArgumentException::class.java) { BackupJson.decode(invalid, games) }
        }
    }

    private suspend fun import(tools: CollectionBackupUseCase, text: String) {
        shadowOf(context.contentResolver).registerInputStream(address, ByteArrayInputStream(text.toByteArray()))
        tools.import(address.toString())
    }

    private fun collection() = CollectionBackup(
        setOf(493),
        mapOf(14 to setOf(493), 15 to setOf(243, 493), 16 to setOf(244, 493)),
        mapOf(
            14 to GuideProgress(setOf("sinnoh-start"), mapOf(481 to "route-201")),
            15 to GuideProgress(setOf("hgss-start"), mapOf(243 to "route-29", 380 to "route-1")),
            16 to GuideProgress(setOf("hgss-start"), mapOf(244 to "route-46", 381 to "route-28"))
        ),
        mapOf(15 to UnownForm.entries.toSet(), 16 to setOf(UnownForm.A)),
        mapOf(15 to setOf(form.identifier), 16 to setOf(form.identifier))
    )
}
