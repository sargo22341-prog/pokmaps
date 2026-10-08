package org.opensources.pokmaps.ui.pokemon

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.opensources.pokmaps.domain.usecase.UnownCollection
import org.opensources.pokmaps.domain.usecase.UnownUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class UnownUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val collection: UnownCollection? = null
)

@HiltViewModel
class UnownViewModel @Inject constructor(private val useCase: UnownUseCase) : ViewModel() {
    private val writeFailed = MutableStateFlow(false)
    val state = combine(useCase.observe(), writeFailed) { collection, failed ->
        UnownUiState(loading = false, failed = failed, collection = collection)
    }.catch { emit(UnownUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), UnownUiState())

    fun toggle(form: UnownForm) {
        val collection = state.value.collection ?: return
        viewModelScope.launch {
            try {
                useCase.setCaught(collection.game, form, form !in collection.caught)
                writeFailed.value = false
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                writeFailed.value = true
            }
        }
    }
}
