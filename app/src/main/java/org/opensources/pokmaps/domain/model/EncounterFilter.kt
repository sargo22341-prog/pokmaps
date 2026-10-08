package org.opensources.pokmaps.domain.model

/** Filtre local de la liste des rencontres, indépendant des marqueurs de la carte. */
enum class EncounterFilter {
    ALL,
    WALK,
    FISHING,
    SURF;

    fun matches(encounter: Encounter): Boolean = when (this) {
        ALL -> true
        WALK -> ObtainMethod.fromEncounterMethod(encounter.method) == ObtainMethod.WALK
        FISHING -> ObtainMethod.fromEncounterMethod(encounter.method) == ObtainMethod.FISHING
        SURF -> ObtainMethod.fromEncounterMethod(encounter.method) == ObtainMethod.SURF
    }
}
