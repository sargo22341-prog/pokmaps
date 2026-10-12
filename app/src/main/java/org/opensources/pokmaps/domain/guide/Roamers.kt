package org.opensources.pokmaps.domain.guide

enum class RoamerCondition { JOHTO, HOENN, RED, BLUE, BULBASAUR, CHARMANDER, SQUIRTLE }

data class RoamerChoice(val pokemonId: Int, val condition: RoamerCondition)

data class RoamerLocation(val identifier: String, val number: Int, val water: Boolean, val north: Boolean)

object Roamers {
    fun choices(version: Int): List<RoamerChoice> = pokemonIds(version).map { pokemon ->
        val condition = when (version) {
            4, 5, 6 -> RoamerCondition.JOHTO

            7, 8 -> RoamerCondition.HOENN

            9 -> if (pokemon == 380) RoamerCondition.RED else RoamerCondition.BLUE

            10, 11 -> when (pokemon) {
                244 -> RoamerCondition.BULBASAUR
                245 -> RoamerCondition.CHARMANDER
                243 -> RoamerCondition.SQUIRTLE
                else -> error("Bête errante inconnue : $pokemon")
            }

            else -> error("Version sans errant : $version")
        }
        RoamerChoice(pokemon, condition)
    }

    fun locations(version: Int): List<RoamerLocation> = places(version).map { identifier ->
        val number = identifier.filter { it.isDigit() }.toInt()
        RoamerLocation(identifier, number, number == 122 || number in 124..134, identifier == "route21-north")
    }

    fun pokemonIds(version: Int): Set<Int> = when (version) {
        4, 5 -> setOf(243, 244, 245)
        6 -> setOf(243, 244)
        7 -> setOf(381)
        8 -> setOf(380)
        9 -> setOf(380, 381)
        10, 11 -> setOf(243, 244, 245)
        else -> emptySet()
    }

    fun places(version: Int): List<String> = when (version) {
        4, 5, 6 -> ((29..39).toList() + (42..46).toList()).map { "route-$it" }
        7, 8, 9 -> (listOf(110, 111) + (117..134).toList()).map { "route$it" }
        10, 11 -> (1..25).map { if (it == 21) "route21-north" else "route$it" }
        else -> emptyList()
    }

    fun maximumObservations(version: Int): Int = when (version) {
        4, 5 -> 3
        6 -> 2
        7, 8, 9, 10, 11 -> 1
        else -> 0
    }

    /** Le choix du partenaire détermine la bête des remakes, jamais la version. */
    fun forStarter(starter: Int): Int = when (starter) {
        1 -> 244
        4 -> 245
        7 -> 243
        else -> error("Partenaire de Kanto inconnu : $starter")
    }

    fun valid(version: Int, observation: RoamerObservation): Boolean =
        observation.pokemonId in pokemonIds(version) && observation.place in places(version)
}
