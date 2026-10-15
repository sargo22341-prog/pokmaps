package org.opensources.pokmaps.di

import android.content.Context
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
            assertEquals(11, games.size)
            assertTrue(games.single { it.versionId == 9 }.forms.getValue(386).single().isDefault)
            assertFalse(context.getDatabasePath("pokedex.db").exists())
            assertFalse(context.getDatabasePath("pokedex-123.db").exists())
            assertTrue(context.getDatabasePath("collection-test.db").exists())
        } finally {
            database.close()
        }
    }
}
