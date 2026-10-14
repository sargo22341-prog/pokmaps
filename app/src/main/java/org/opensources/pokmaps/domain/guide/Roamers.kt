package org.opensources.pokmaps.domain.guide

enum class RoamerCondition { JOHTO, HOENN, RED, BLUE, BULBASAUR, CHARMANDER, SQUIRTLE }

/** Routes que parcourt un errant, d'après les tables de déplacement du moteur de chaque jeu. */
enum class RoamerArea { JOHTO, HOENN, KANTO }

data class RoamerChoice(val pokemonId: Int, val condition: RoamerCondition)

/**
 * Pokémon errants de chaque version, présentés dans un article des quêtes annexes. Leur prochaine route n'est
 * pas prévisible : aucune position n'est suivie.
 */
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

    fun pokemonIds(version: Int): List<Int> = when (version) {
        4, 5 -> listOf(243, 244, 245)
        6 -> listOf(243, 244)
        7 -> listOf(381)
        8 -> listOf(380)
        9 -> listOf(380, 381)
        10, 11 -> listOf(243, 244, 245)
        else -> emptyList()
    }

    /** Niveau de la rencontre : 40 à Johto et Hoenn, 50 dans les remakes. */
    fun level(version: Int): Int = when (version) {
        4, 5, 6, 7, 8, 9 -> 40
        10, 11 -> 50
        else -> error("Version sans errant : $version")
    }

    fun area(version: Int): RoamerArea = when (version) {
        4, 5, 6 -> RoamerArea.JOHTO
        7, 8, 9 -> RoamerArea.HOENN
        10, 11 -> RoamerArea.KANTO
        else -> error("Version sans errant : $version")
    }

    /** Article des quêtes annexes qui présente les errants de la version, null sans errant. */
    fun article(version: Int): String? = when (version) {
        4, 5, 6 -> "johto-roamers"
        7, 8, 9 -> "hoenn-roamers"
        10, 11 -> "remake-roamers"
        else -> null
    }
}
