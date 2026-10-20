package org.opensources.pokmaps.domain.model

/** Ordre commun aux rencontres aquatiques de toutes les générations. */
enum class WaterMethod(val identifier: String) {
    SURF("surf"),
    OLD_ROD("old-rod"),
    GOOD_ROD("good-rod"),
    SUPER_ROD("super-rod");

    companion object {
        fun of(identifier: String): WaterMethod? = entries.firstOrNull { it.identifier == identifier }
    }
}
