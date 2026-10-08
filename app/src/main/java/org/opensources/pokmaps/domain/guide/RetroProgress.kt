package org.opensources.pokmaps.domain.guide

data class RetroProgress(
    val username: String? = null,
    val earned: Map<Int, Set<Int>> = emptyMap(),
    val hardcore: Map<Int, Set<Int>> = emptyMap(),
    val synchronizedAt: Long? = null
)

/** Identifiants des ensembles officiels, sans jeux modifiés ni sous-ensembles. */
object RetroGames {
    val ids: Map<Int, Int> = mapOf(1 to 724, 2 to 586, 3 to 723, 4 to 576, 5 to 722, 6 to 810)
}
