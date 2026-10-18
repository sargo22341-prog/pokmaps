package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.GameVersion

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
        val condition = when (GameVersion.of(version)) {
            GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> RoamerCondition.JOHTO

            GameVersion.RUBY, GameVersion.SAPPHIRE -> RoamerCondition.HOENN

            GameVersion.EMERALD -> if (pokemon == 380) RoamerCondition.RED else RoamerCondition.BLUE

            GameVersion.FIRERED, GameVersion.LEAFGREEN -> when (pokemon) {
                244 -> RoamerCondition.BULBASAUR
                245 -> RoamerCondition.CHARMANDER
                243 -> RoamerCondition.SQUIRTLE
                else -> error("Bête errante inconnue : $pokemon")
            }

            GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error("Outil Sinnoh non disponible")

            GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
        }
        RoamerChoice(pokemon, condition)
    }

    fun pokemonIds(version: Int): List<Int> = when (GameVersion.of(version)) {
        GameVersion.GOLD, GameVersion.SILVER -> listOf(243, 244, 245)
        GameVersion.CRYSTAL -> listOf(243, 244)
        GameVersion.RUBY -> listOf(381)
        GameVersion.SAPPHIRE -> listOf(380)
        GameVersion.EMERALD -> listOf(380, 381)
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> listOf(243, 244, 245)
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error("Outil Sinnoh non disponible")
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> emptyList()
    }

    /** Niveau de la rencontre : 40 à Johto et Hoenn, 50 dans les remakes. */
    fun level(version: Int): Int = when (GameVersion.of(version)) {
        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL, GameVersion.RUBY, GameVersion.SAPPHIRE,
        GameVersion.EMERALD -> 40

        GameVersion.FIRERED, GameVersion.LEAFGREEN -> 50

        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error("Outil Sinnoh non disponible")

        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
    }

    fun area(version: Int): RoamerArea = when (GameVersion.of(version)) {
        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> RoamerArea.JOHTO
        GameVersion.RUBY, GameVersion.SAPPHIRE, GameVersion.EMERALD -> RoamerArea.HOENN
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> RoamerArea.KANTO
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error("Outil Sinnoh non disponible")
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
    }

    /** Article des quêtes annexes qui présente les errants de la version, null sans errant. */
    fun article(version: Int): String? = when (GameVersion.of(version)) {
        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> "johto-roamers"
        GameVersion.RUBY, GameVersion.SAPPHIRE, GameVersion.EMERALD -> "hoenn-roamers"
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> "remake-roamers"
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error("Outil Sinnoh non disponible")
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> null
    }
}
