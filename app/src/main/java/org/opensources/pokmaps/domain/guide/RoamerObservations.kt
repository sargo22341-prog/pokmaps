package org.opensources.pokmaps.domain.guide

/** Dernière route relevée à la main ; elle ne prédit jamais le déplacement suivant. */
object RoamerObservations {
    val places: List<String> = (201..222).filter { it !in setOf(204, 205, 210, 211, 212) }.map { "route-$it" } +
        listOf(
            "route-204-south", "route-204-north", "route-205-south", "route-205-north",
            "route-210-south", "route-210-north", "route-211-west", "route-211-east",
            "route-212-north", "route-212-south", "valley-windworks", "fuego-ironworks"
        )

    fun places(version: Int, pokemon: Int): List<String> = if (version in 15..16) {
        val routes = if (pokemon in setOf(243, 244)) {
            (29..39).toList() + (42..46).toList()
        } else {
            (1..22).toList() + listOf(24, 26, 28)
        }
        routes.map { "route-$it" }
    } else {
        places
    }

    fun validate(version: Int, observations: Map<Int, String>) {
        require(observations.isEmpty() || version in 12..16)
        if (observations.isEmpty()) return
        require(observations.keys.all { it in Roamers.pokemonIds(version) })
        require(observations.all { (pokemon, place) -> place in places(version, pokemon) })
    }
}
