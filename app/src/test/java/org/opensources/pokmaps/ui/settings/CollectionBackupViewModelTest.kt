package org.opensources.pokmaps.ui.settings

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.domain.usecase.CollectionDocuments
import org.opensources.pokmaps.ui.MainDispatcherRule

class CollectionBackupViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test
    fun startsReadyAndDistinguishesBothSuccessesFromFailure() = runTest {
        val documents = MemoryDocuments()
        val model = CollectionBackupViewModel(documents)
        assertEquals(BackupUiState.READY, model.state.value)
        model.export("content://export")
        assertEquals(BackupUiState.EXPORTED, model.state.value)
        model.import("content://import")
        assertEquals(BackupUiState.IMPORTED, model.state.value)
        documents.failing = true
        model.import("content://invalid")
        assertEquals(BackupUiState.ERROR, model.state.value)
    }
}

private class MemoryDocuments : CollectionDocuments {
    var failing = false
    override suspend fun export(address: String) {
        check(!failing)
    }
    override suspend fun import(address: String) {
        check(!failing)
    }
}
