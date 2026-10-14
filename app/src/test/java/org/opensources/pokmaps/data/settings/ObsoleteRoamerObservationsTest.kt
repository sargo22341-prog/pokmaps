package org.opensources.pokmaps.data.settings

import androidx.datastore.preferences.core.mutablePreferencesOf
import androidx.datastore.preferences.core.stringSetPreferencesKey
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ObsoleteRoamerObservationsTest {
    @Test
    fun removesOnlyTheObservationsOfEveryVersion() = runTest {
        val completed = stringSetPreferencesKey("guide_completed_9")
        val stored = mutablePreferencesOf(
            stringSetPreferencesKey("guide_roamers_4") to setOf("243:route-29"),
            stringSetPreferencesKey("guide_roamers_9") to setOf("380:route110"),
            completed to setOf("hoenn-start")
        )
        assertTrue(ObsoleteRoamerObservations.shouldMigrate(stored))

        val migrated = ObsoleteRoamerObservations.migrate(stored)

        assertEquals(setOf(completed), migrated.asMap().keys)
        assertEquals(setOf("hoenn-start"), migrated[completed])
        assertFalse(ObsoleteRoamerObservations.shouldMigrate(migrated))
    }
}
