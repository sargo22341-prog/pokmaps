package org.opensources.pokmaps.domain.model

/** Provenance externe relue par le pipeline, conservée dans les notes et conditions françaises. */
object ExternalEvent {
    fun mentioned(text: String?): Boolean = text?.contains("événement externe", ignoreCase = true) == true

    fun method(identifier: String): Boolean = identifier in METHODS

    fun map(identifier: String): Boolean = MAPS.any { identifier == it || identifier.startsWith("$it-") }

    private val METHODS = setOf("colosseum-bonus-disc-jpn", "colosseum-bonus-disc-us", "pokemon-channel-pal")
    private val MAPS = setOf("faraway-island", "birth-island", "navel-rock", "southern-island")
}
