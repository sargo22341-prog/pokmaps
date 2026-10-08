package org.opensources.pokmaps.data.settings

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.guide.RetroProgress

class RetroSettingsTest {
    @Test
    fun disconnectClearsOnlyRemoteProgressAndKeepsLocalCollectionAndGuides() = runTest {
        val store = FakeDataStore()
        val collection = CollectionSettings(store)
        val guide = GuideSettings(store)
        val retro = RetroSettings(store)
        collection.setCaught(setOf(1), 25, true)
        guide.complete(1, "ra-4401", true)
        retro.save(RetroProgress("player", mapOf(1 to setOf(4401)), mapOf(1 to setOf(4401)), 1))
        assertEquals(setOf(4401), retro.progress.first().earned[1])
        retro.reset(null)
        assertEquals(RetroProgress(), retro.progress.first())
        assertEquals(setOf(25), collection.caughtByVersion.first()[1])
        assertTrue("ra-4401" in guide.progress(1).first().completed)
    }
}
