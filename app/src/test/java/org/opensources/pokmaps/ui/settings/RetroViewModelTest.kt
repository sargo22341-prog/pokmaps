package org.opensources.pokmaps.ui.settings

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.domain.guide.RetroProgress
import org.opensources.pokmaps.domain.usecase.RetroConnection
import org.opensources.pokmaps.ui.MainDispatcherRule

class RetroViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test
    fun disconnectedStateNeverStartsANetworkRequest() = runTest {
        val connection = MemoryConnection()
        val model = RetroViewModel(connection)
        assertFalse(model.state.value.loading)
        assertFalse(model.state.value.failed)
        assertEquals(null, model.state.value.progress.username)
        assertEquals(0, connection.requests)
    }

    @Test
    fun failedSynchronizationPreservesCachedProgress() = runTest {
        val connection = MemoryConnection()
        connection.progress.value = RetroProgress("player", mapOf(1 to setOf(1, 2)), mapOf(1 to setOf(2)), 1)
        val model = RetroViewModel(connection)
        model.onAction(RetroAction.Synchronize)
        assertTrue(model.state.value.failed)
        assertFalse(model.state.value.busy)
        assertEquals(2, model.state.value.earnedCount)
        assertEquals(1, model.state.value.hardcoreCount)
        assertEquals(1, connection.requests)
    }

    @Test
    fun unreadableCredentialsHaveAnErrorAndCanBeRetried() = runTest {
        val connection = MemoryConnection()
        connection.failing = true
        val model = RetroViewModel(connection)
        assertTrue(model.state.value.failed)
        connection.failing = false
        model.onAction(RetroAction.Retry)
        assertFalse(model.state.value.failed)
        model.onAction(RetroAction.Connect("player", "a".repeat(32)))
        assertEquals("player", model.state.value.progress.username)
        assertEquals(1, model.state.value.connectionRevision)
        model.onAction(RetroAction.Disconnect)
        assertEquals(null, model.state.value.progress.username)
        assertEquals(0, connection.requests)
    }
}

private class MemoryConnection : RetroConnection {
    val progress = MutableStateFlow(RetroProgress())
    var failing = false
    var requests = 0
    override fun observe(): Flow<RetroProgress> = if (failing) flow { error("Clé illisible") } else progress
    override suspend fun connect(username: String, apiKey: String) {
        progress.value = RetroProgress(username)
    }
    override suspend fun disconnect() {
        progress.value = RetroProgress()
    }
    override suspend fun synchronize() {
        requests += 1
        error("Hors ligne")
    }
}
