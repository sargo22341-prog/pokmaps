package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.GameVersion

enum class RoamerCondition { JOHTO, HOENN, RED, BLUE, BULBASAUR, CHARMANDER, SQUIRTLE, MESPRIT, CRESSELIA, BIRDS }

/** Routes que parcourt un errant, d'après les tables de déplacement du moteur de chaque jeu. */
enum class RoamerArea { JOHTO, HOENN, KANTO, SINNOH }

data class RoamerChoice(val pokemonId: Int, val condition: RoamerCondition)

/**
 * Pokémon errants de chaque version, présentés dans un article des quêtes annexes. Leur prochaine route n'est
 * pas prévisible ; les observations manuelles de Sinnoh restent distinctes des positions du moteur.
 */
object Roamers {
    fun choices(version: Int): List<RoamerChoice> = pokemonIds(version).map { pokemon ->
        val condition = when (GameVersion.of(version)) {
            GameVersion.HEARTGOLD, GameVersion.SOULSILVER -> error("Suivi des errants HGSS non disponible")

            GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> RoamerCondition.JOHTO

            GameVersion.RUBY, GameVersion.SAPPHIRE -> RoamerCondition.HOENN

            GameVersion.EMERALD -> if (pokemon == 380) RoamerCondition.RED else RoamerCondition.BLUE

            GameVersion.FIRERED, GameVersion.LEAFGREEN -> when (pokemon) {
                244 -> RoamerCondition.BULBASAUR
                245 -> RoamerCondition.CHARMANDER
                243 -> RoamerCondition.SQUIRTLE
                else -> error("Bête errante inconnue : $pokemon")
            }

            GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> when (pokemon) {
                481 -> RoamerCondition.MESPRIT
                488 -> RoamerCondition.CRESSELIA
                144, 145, 146 -> RoamerCondition.BIRDS
                else -> error("Errant Sinnoh inconnu : $pokemon")
            }

            GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
        }
        RoamerChoice(pokemon, condition)
    }

    fun pokemonIds(version: Int): List<Int> = when (GameVersion.of(version)) {
        GameVersion.HEARTGOLD, GameVersion.SOULSILVER -> error("Suivi des errants HGSS non disponible")
        GameVersion.GOLD, GameVersion.SILVER -> listOf(243, 244, 245)
        GameVersion.CRYSTAL -> listOf(243, 244)
        GameVersion.RUBY -> listOf(381)
        GameVersion.SAPPHIRE -> listOf(380)
        GameVersion.EMERALD -> listOf(380, 381)
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> listOf(243, 244, 245)
        GameVersion.DIAMOND, GameVersion.PEARL -> listOf(481, 488)
        GameVersion.PLATINUM -> listOf(481, 488, 144, 145, 146)
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> emptyList()
    }

    /** Niveau de la rencontre : 40 à Johto et Hoenn, 50 dans les remakes. */
    fun level(version: Int): Int = when (GameVersion.of(version)) {
        GameVersion.HEARTGOLD, GameVersion.SOULSILVER -> error("Suivi des errants HGSS non disponible")

        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL, GameVersion.RUBY, GameVersion.SAPPHIRE,
        GameVersion.EMERALD -> 40

        GameVersion.FIRERED, GameVersion.LEAFGREEN -> 50

        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> 50

        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
    }

    fun level(version: Int, pokemon: Int): Int {
        require(pokemon in pokemonIds(version))
        return if (version == 14 && pokemon in 144..146) 60 else level(version)
    }

    fun area(version: Int): RoamerArea = when (GameVersion.of(version)) {
        GameVersion.HEARTGOLD, GameVersion.SOULSILVER -> error("Suivi des errants HGSS non disponible")
        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> RoamerArea.JOHTO
        GameVersion.RUBY, GameVersion.SAPPHIRE, GameVersion.EMERALD -> RoamerArea.HOENN
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> RoamerArea.KANTO
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> RoamerArea.SINNOH
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> error("Version sans errant : $version")
    }

    /** Article des quêtes annexes qui présente les errants de la version, null sans errant. */
    fun article(version: Int): String? = when (GameVersion.of(version)) {
        GameVersion.HEARTGOLD, GameVersion.SOULSILVER -> error("Suivi des errants HGSS non disponible")
        GameVersion.GOLD, GameVersion.SILVER, GameVersion.CRYSTAL -> "johto-roamers"
        GameVersion.RUBY, GameVersion.SAPPHIRE, GameVersion.EMERALD -> "hoenn-roamers"
        GameVersion.FIRERED, GameVersion.LEAFGREEN -> "remake-roamers"
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> "sinnoh-roamers"
        GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW -> null
    }
}
