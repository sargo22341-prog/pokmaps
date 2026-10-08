package org.opensources.pokmaps.domain.guide

object Roamers {
    val routes: List<Int> = (29..39).toList() + (42..46).toList()
    val places: Set<String> = routes.map { "route-$it" }.toSet()
    val pokemonIds: Set<Int> = setOf(243, 244, 245)
}
