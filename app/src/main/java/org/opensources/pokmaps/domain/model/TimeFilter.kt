package org.opensources.pokmaps.domain.model

/** Choix unique de l'heure ; Tout conserve les couleurs originales. */
enum class TimeFilter(val time: EncounterTime?) {
    MORNING(EncounterTime.MORNING),
    DAY(EncounterTime.DAY),
    NIGHT(EncounterTime.NIGHT),
    ALL(null);

    val times: Set<EncounterTime> get() = time?.let { setOf(it) } ?: EncounterTime.entries.toSet()

    fun next(): TimeFilter = when (this) {
        MORNING -> DAY
        DAY -> NIGHT
        NIGHT -> ALL
        ALL -> MORNING
    }
}
