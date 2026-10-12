package org.opensources.pokmaps.ui.common

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class CollectionWritesTest {
    @Test
    fun cancellationCancelsTheWritingJob() = runTest(UnconfinedTestDispatcher()) {
        val writes = CollectionWrites(backgroundScope)
        var job: Job? = null
        writes.launch {
            job = currentCoroutineContext()[Job]
            throw CancellationException("Annulation")
        }
        assertTrue(checkNotNull(job).isCancelled)
        assertFalse(writes.failed.value)
    }
}
