package org.opensources.pokmaps.di

import android.content.Context
import android.content.pm.PackageManager
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class DataModuleTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun applicationUpdateReplacesTheAssetCopyWithoutChangingStoredProgress() = runBlocking {
        val store = SettingsModule.settings(context)
        store.edit { preferences ->
            preferences[stringSetPreferencesKey("caught_pokemon_4")] = setOf("25")
            preferences[stringSetPreferencesKey("caught_pokemon_15")] = setOf("493")
            preferences[stringSetPreferencesKey("caught_unown_16")] = setOf("a", "exclamation")
            preferences[stringSetPreferencesKey("guide_completed_15")] = setOf("hgss-start")
            preferences[stringSetPreferencesKey("sinnoh_roamers_15")] = setOf("243:route-29")
        }
        val before = store.data.first()
        val info = context.packageManager.getPackageInfo(context.packageName, PackageManager.PackageInfoFlags.of(0))
        val originalTime = info.lastUpdateTime
        val oldName = "pokedex-$originalTime.db"
        val first = DataModule.database(context)
        try {
            withContext(Dispatchers.IO) { first.gameDao().games().first() }
        } finally {
            first.close()
        }
        info.lastUpdateTime = originalTime + 1
        org.robolectric.Shadows.shadowOf(context.packageManager).installPackage(info)
        val updated = DataModule.database(context)
        try {
            val games = withContext(Dispatchers.IO) { updated.gameDao().games().first() }
            assertEquals(14, games.size)
            assertFalse(context.getDatabasePath(oldName).exists())
            assertTrue(context.getDatabasePath("pokedex-${originalTime + 1}.db").exists())
            assertEquals(before, store.data.first())
        } finally {
            updated.close()
        }
    }

    @Test
    fun creatingTheProviderDoesNotCreateOrDeleteAnyDatabase() {
        context.openOrCreateDatabase("pokedex.db", Context.MODE_PRIVATE, null).close()
        val before = context.databaseList().toSet()
        val database = DataModule.database(context)
        try {
            assertEquals(before, context.databaseList().toSet())
        } finally {
            database.close()
        }
    }

    @Test
    fun openingTheNewCopyPreservesUnrelatedDatabasesAndLoadsBundledData() = runBlocking {
        context.openOrCreateDatabase("pokedex.db", Context.MODE_PRIVATE, null).close()
        context.openOrCreateDatabase("pokedex-123.db", Context.MODE_PRIVATE, null).close()
        context.openOrCreateDatabase("collection-test.db", Context.MODE_PRIVATE, null).close()
        val database = DataModule.database(context)
        try {
            val games = withContext(Dispatchers.IO) { database.gameDao().games().first() }
            assertEquals(14, games.size)
            assertTrue(games.single { it.versionId == 9 }.forms.getValue(386).single().isDefault)
            assertFalse(context.getDatabasePath("pokedex.db").exists())
            assertFalse(context.getDatabasePath("pokedex-123.db").exists())
            assertTrue(context.getDatabasePath("collection-test.db").exists())
        } finally {
            database.close()
        }
    }
}
