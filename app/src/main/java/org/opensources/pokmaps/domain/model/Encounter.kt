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
    val conditions: String?
) {
    /** Les échanges n'ont pas de niveau significatif (le Pokémon garde celui de l'échange). */
    val isTrade: Boolean get() = method == TRADE

    private companion object {
        const val TRADE = "npc-trade"
    }
}

/** Rencontres d'une zone (ou d'un Pokémon) regroupées par méthode, dans l'ordre du jeu. */
data class EncounterGroup(val methodName: String, val encounters: List<Encounter>)

fun List<Encounter>.groupByMethod(): List<EncounterGroup> = sortedWith(
    compareBy<Encounter> { it.methodOrder }
        .thenByDescending { it.chance ?: 0.0 }
        .thenBy { it.areaName }
        .thenBy { it.pokemonId }
).groupBy { it.methodName }.map { (method, encounters) -> EncounterGroup(method, encounters) }
