package org.opensources.pokmaps.domain.model

/** Tables de rencontres selon l'heure du jeu, indépendantes des palettes des cartes. */
enum class EncounterTime(val identifier: String) {
    MORNING("time-morning"),
    DAY("time-day"),
    NIGHT("time-night");

    companion object {
        fun fromCondition(identifier: String): EncounterTime? = entries.firstOrNull { it.identifier == identifier }
    }
}

fun Encounter.matchesTimes(selected: Set<EncounterTime>): Boolean = times.isEmpty() || times.any { it in selected }
