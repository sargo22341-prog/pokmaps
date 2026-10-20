package org.opensources.pokmaps.domain.guide

data class RetroProgress(
    val username: String? = null,
    val earned: Map<Int, Set<Int>> = emptyMap(),
    val hardcore: Map<Int, Set<Int>> = emptyMap(),
    val synchronizedAt: Long? = null
)

/** Identifiants des ensembles officiels, sans jeux modifiés ni sous-ensembles. */
object RetroGames {
    val ids: Map<Int, Int> = mapOf(
        1 to 724, 2 to 586, 3 to 723, 4 to 576, 5 to 722, 6 to 810,
        7 to 790, 8 to 791, 9 to 668, 10 to 515, 11 to 788,
        12 to 9852, 13 to 25369, 14 to 11732
    )
}
