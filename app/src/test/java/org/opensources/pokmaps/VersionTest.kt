package org.opensources.pokmaps

import org.junit.Assert.assertTrue
import org.junit.Test

class VersionTest {
    @Test
    fun versionNameIsDefined() {
        assertTrue(BuildConfig.VERSION_NAME.isNotBlank())
    }
}
