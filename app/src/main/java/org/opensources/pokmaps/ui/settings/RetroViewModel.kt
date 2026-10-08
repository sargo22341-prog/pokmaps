package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.guide.RetroProgress
import org.opensources.pokmaps.domain.usecase.RetroConnection
import org.opensources.pokmaps.domain.usecase.RetroUseCase

data class RetroUiState(
    val loading: Boolean = true,
    val busy: Boolean = false,
    val failed: Boolean = false,
    val progress: RetroProgress = RetroProgress(),
    val connectionRevision: Int = 0
) {
    val earnedCount: Int = progress.earned.values.sumOf { it.size }
    val hardcoreCount: Int = progress.hardcore.values.sumOf { it.size }
}

sealed interface RetroAction {
    class Connect(val username: String, val apiKey: String) : RetroAction
    data object Disconnect : RetroAction
    data object Synchronize : RetroAction
    data object Retry : RetroAction
}

@HiltViewModel
class RetroViewModel internal constructor(private val connection: RetroConnection) : ViewModel() {
    @Inject constructor(connection: RetroUseCase) : this(connection as RetroConnection)

    private val mutableState = MutableStateFlow(RetroUiState())
    val state: StateFlow<RetroUiState> = mutableState.asStateFlow()
    private var loadJob: Job? = null
    private var operation: Job? = null

    init {
        observe()
    }

    fun onAction(action: RetroAction) {
        when (action) {
            is RetroAction.Connect -> perform {
                connection.connect(action.username, action.apiKey)
                mutableState.update { it.copy(connectionRevision = it.connectionRevision + 1) }
                observe()
            }

            RetroAction.Disconnect -> perform { connection.disconnect() }

            RetroAction.Synchronize -> perform { connection.synchronize() }

            RetroAction.Retry -> observe()
        }
    }

    private fun observe() {
        loadJob?.cancel()
        mutableState.update { it.copy(loading = true, failed = false) }
        loadJob = viewModelScope.launch {
            attempt {
                connection.observe().collect { progress ->
                    mutableState.update { it.copy(loading = false, progress = progress) }
                }
            }
        }
    }

    private fun perform(block: suspend () -> Unit) {
        val previous = operation
        previous?.cancel()
        operation = viewModelScope.launch {
            previous?.join()
            mutableState.update { it.copy(busy = true, failed = false) }
            try {
                attempt(block)
            } finally {
                mutableState.update { it.copy(busy = false) }
            }
        }
    }

    private suspend fun attempt(block: suspend () -> Unit) {
        try {
            block()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            // Ne jamais afficher l'exception réseau : son URL peut contenir la clé.
            mutableState.update { it.copy(loading = false, failed = true) }
        }
    }
}
