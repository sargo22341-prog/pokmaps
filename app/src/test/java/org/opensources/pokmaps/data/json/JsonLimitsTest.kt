package org.opensources.pokmaps.data.json

import org.junit.Test

class JsonLimitsTest {
    @Test
    fun bracesInsideEscapedStringsAreNotNesting() {
        JsonLimits.validate("""{"label":"[\\\"{{{{{{{{{{{{{{{{{{{{{{{{{{"}""", 100)
    }

    @Test(expected = IllegalArgumentException::class)
    fun deeplyNestedDocumentsAreRejectedBeforeTheParser() {
        JsonLimits.validate("[".repeat(17) + "0" + "]".repeat(17), 100)
    }

    @Test(expected = IllegalArgumentException::class)
    fun truncatedDocumentsAreRejected() {
        JsonLimits.validate("""{"label":"texte""", 100)
    }
}
