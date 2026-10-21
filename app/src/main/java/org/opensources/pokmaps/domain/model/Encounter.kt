package org.opensources.pokmaps.domain.model

/**
 * Rencontre d'un Pokémon dans une zone et une version : niveaux, probabilité (en %, null pour un don,
 * un Pokémon fixe ou un échange), nombre d'exemplaires et notes.
 */
data class Encounter(
    val versionId: Int,
    val versionName: String,
    val areaId: Int,
    val areaName: String,
    val pokemonId: Int,
    val pokemonName: String,
    val method: String,
    val methodName: String,
    val methodOrder: Int,
    val isOneOff: Boolean,
    val minLevel: Int,
    val maxLevel: Int,
    val chance: Double?,
    val quantity: Int,
    val note: String?,
    val conditions: String?,
    val times: Set<EncounterTime> = emptySet(),
    val nonTimeConditions: String? = conditions,
    val isExternalEvent: Boolean = false,
    val conditionKeys: Set<String> = emptySet(),
    val conditionNames: Map<String, String> = emptyMap(),
    val habitat: EncounterHabitat = EncounterHabitat.TALL_GRASS
) {
    val needsExternalEventLabel: Boolean
        get() = isExternalEvent && !ExternalEvent.mentioned(note) && !ExternalEvent.mentioned(conditions)

    /** Les échanges n'ont pas de niveau significatif (le Pokémon garde celui de l'échange). */
    val isTrade: Boolean get() = method == TRADE

    /** Rencontre à l'état sauvage (herbes, grottes, surf, pêche), et non don, échange ou Pokémon fixe. */
    val isWild: Boolean get() = ObtainMethod.fromEncounterMethod(method).isWild

    val isWater: Boolean get() = method in WATER_METHODS

    val hasTimeOfDay: Boolean = when (GameVersion.of(versionId).generation) {
        Generation.GEN1, Generation.GEN3 -> false
        Generation.GEN2, Generation.GEN4 -> true
    }

    private companion object {
        const val TRADE = "npc-trade"
        val WATER_METHODS = setOf("surf", "old-rod", "good-rod", "super-rod", "feebas-tile-fishing", "seaweed")
    }
}

/** Pokémon qu'on rencontre à l'état sauvage parmi ces rencontres. */
fun List<Encounter>.wildPokemonIds(): Set<Int> = filter { it.isWild }.map { it.pokemonId }.toSet()

/** Rencontres d'une zone (ou d'un Pokémon) regroupées par méthode, dans l'ordre du jeu. */
data class EncounterGroup(val methodName: String, val encounters: List<Encounter>) {
    val habitat: EncounterHabitat = encounters.firstOrNull()?.habitat ?: EncounterHabitat.GRASS
    val aquatic: Boolean = encounters.isNotEmpty() && encounters.all {
        WaterMethod.of(it.method) != null || it.method == "feebas-tile-fishing"
    }
    val water: Boolean = encounters.isNotEmpty() && encounters.all { it.isWater }
    val headbutt: Boolean = encounters.any { it.method.startsWith("headbutt") }
    val honeyTrees: Boolean = encounters.any { it.method == "honey-tree" }
    val landscape: Boolean = encounters.any { it.isWild }
    val species: List<TimedSpecies> = encounters.groupBy { Triple(it.versionId, it.areaId, it.pokemonId) }
        .values.map { variants -> TimedSpecies(variants.first().pokemonId, variants.first().pokemonName, variants) }
}

fun List<Encounter>.groupByMethod(): List<EncounterGroup> = sortedWith(
    compareBy<Encounter> { it.methodOrder }
        .thenByDescending { it.chance ?: 0.0 }
        .thenBy { it.areaName }
        .thenBy { it.pokemonId }
).groupBy {
    when {
        WaterMethod.of(it.method) != null || it.method == "feebas-tile-fishing" -> ""
        it.method.startsWith("headbutt") || it.method == "honey-tree" -> "headbutt"
        else -> it.methodName
    }
}
    .map { (method, encounters) -> EncounterGroup(method, encounters) }
    .sortedWith(compareBy<EncounterGroup> { it.water }.thenBy { it.habitat != EncounterHabitat.FOREST })
