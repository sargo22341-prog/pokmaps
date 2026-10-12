package org.opensources.pokmaps.ui.common

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Une écriture échouée conserve les valeurs observées et permet une nouvelle tentative. */
internal class CollectionWrites(private val scope: CoroutineScope) {
    private val mutableFailed = MutableStateFlow(false)
    val failed = mutableFailed.asStateFlow()

    fun launch(block: suspend () -> Unit) {
        scope.launch {
            try {
                block()
                mutableFailed.value = false
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                mutableFailed.value = true
            }
        }
    }
}
