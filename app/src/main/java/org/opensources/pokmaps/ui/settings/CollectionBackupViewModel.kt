package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.usecase.CollectionBackupUseCase
import org.opensources.pokmaps.domain.usecase.CollectionDocuments

enum class BackupUiState { READY, BUSY, EXPORTED, IMPORTED, ERROR }

@HiltViewModel
class CollectionBackupViewModel internal constructor(private val documents: CollectionDocuments) : ViewModel() {
    @Inject constructor(documents: CollectionBackupUseCase) : this(documents as CollectionDocuments)

    private val mutableState = MutableStateFlow(BackupUiState.READY)
    val state: StateFlow<BackupUiState> = mutableState.asStateFlow()

    fun export(address: String) = perform(BackupUiState.EXPORTED) { documents.export(address) }
    fun import(address: String) = perform(BackupUiState.IMPORTED) { documents.import(address) }

    private fun perform(success: BackupUiState, block: suspend () -> Unit) {
        if (state.value == BackupUiState.BUSY) return
        mutableState.value = BackupUiState.BUSY
        viewModelScope.launch {
            try {
                block()
                mutableState.value = success
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                mutableState.value = BackupUiState.ERROR
            }
        }
    }
}
