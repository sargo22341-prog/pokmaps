package org.opensources.pokmaps.data.settings

import android.content.Context
import android.net.Uri
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.test.core.app.ApplicationProvider
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf

@RunWith(RobolectricTestRunner::class)
class CollectionBackupRepositoryTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val games = listOf(FakeGameDao.RED) + FakeGameDao.GBA_GAMES
    private val address = Uri.parse("content://collection/document")

    @Test
    fun documentExportAndImportPreserveEveryGbaVersionAndBothUnownCollections() = runTest {
        val backup = CollectionBackup(
            (1..386).toSet(),
            (7..11).associateWith { (1..386).toSet() },
            emptyMap(),
            (10..11).associateWith { UnownForm.entries.toSet() }
        )
        val imported = FakeDataStore()
        importText(imported, BackupJson.encode(backup))
        val output = ByteArrayOutputStream()
        shadowOf(context.contentResolver).registerOutputStream(address, output)
        repository(imported).export(address.toString())
        val exported = BackupJson.decode(output.toString(Charsets.UTF_8), games)
        assertEquals(backup.favorites, exported.favorites)
        for (version in 7..11) assertEquals(backup.caught[version], exported.caught[version])
        assertEquals(backup.unown, exported.unown)
        val restored = FakeDataStore()
        importText(restored, output.toString(Charsets.UTF_8))
        assertEquals(imported.data.first(), restored.data.first())
    }

    @Test
    fun oldDocumentWithoutUnownMergesAtomicallyWithNewGames() = runTest {
        val store = FakeDataStore()
        store.edit { it[stringSetPreferencesKey("caught_pokemon_11")] = setOf("386") }
        importText(
            store,
            """{"format":"pokmaps-collection","schema":1,"favorites":[25],"games":[
                {"version":1,"caught":[25],"completed":[],"roamers":[]}
            ]}"""
        )
        val collection = CollectionSettings(store)
        assertEquals(setOf(25), collection.favorites.first())
        assertEquals(setOf(25), collection.caughtByVersion.first()[1])
        assertEquals(setOf(386), collection.caughtByVersion.first()[11])
    }

    @Test
    fun invalidDocumentLeavesExistingPreferencesUntouched() = runTest {
        val store = FakeDataStore()
        store.edit { it[stringSetPreferencesKey("caught_pokemon_11")] = setOf("386") }
        val before = store.data.first()
        val invalid = """{"format":"pokmaps-collection","schema":1,"favorites":[],"games":[
            {"version":7,"caught":[387],"completed":[],"roamers":[]}
        ]}"""
        try {
            importText(store, invalid)
            throw AssertionError("Une espèce hors du National doit être refusée")
        } catch (_: IllegalArgumentException) {
            assertEquals(before, store.data.first())
        }
    }

    private fun repository(store: FakeDataStore) = CollectionBackupRepository(context, store, FakeGameDao(games))

    private suspend fun importText(store: FakeDataStore, text: String) {
        shadowOf(context.contentResolver).registerInputStream(address, ByteArrayInputStream(text.toByteArray()))
        repository(store).import(address.toString())
    }
}
