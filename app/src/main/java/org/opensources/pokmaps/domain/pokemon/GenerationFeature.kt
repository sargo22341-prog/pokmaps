package org.opensources.pokmaps.domain.pokemon

/**
 * Mécaniques apparues après la 1re génération, avec la génération qui les introduit : la fiche d'un Pokémon ne
 * les montre que pour un jeu qui les connaît.
 */
enum class GenerationFeature(val introducedIn: Int) {
    /** Objets tenus par les Pokémon sauvages. */
    HELD_ITEMS(2),

    /** Pokémon chromatiques. */
    SHINY(2),

    /** Pokémon mâles et femelles. */
    GENDER(2),

    /** Œufs : groupes d'œufs et cycles d'éclosion. */
    BREEDING(2),

    /** Talents ; le talent caché arrive en 5e génération. */
    ABILITIES(3);

    fun existsIn(generationId: Int): Boolean = generationId >= introducedIn
}

/** Probabilité de rencontrer un Pokémon chromatique : 1 chance sur [oneIn]. */
object ShinyOdds {
    private const val CLASSIC_ODDS = 8192
    private const val MODERN_ODDS = 4096
    private const val MODERN_ODDS_GENERATION = 6

    /** 1 sur 8 192 de la 2e à la 5e génération, 1 sur 4 096 ensuite ; null avant les chromatiques. */
    fun oneIn(generationId: Int): Int? = when {
        !GenerationFeature.SHINY.existsIn(generationId) -> null
        generationId < MODERN_ODDS_GENERATION -> CLASSIC_ODDS
        else -> MODERN_ODDS
    }
}

/** Répartition des sexes : `femaleEighths` huitièmes de femelles (0 à 8), ou asexué. */
sealed interface GenderRatio {
    data object Genderless : GenderRatio

    data class Gendered(val femaleEighths: Int) : GenderRatio {
        val femalePercent: Double get() = femaleEighths * PERCENT / EIGHTHS
        val malePercent: Double get() = PERCENT - femalePercent
    }

    companion object {
        private const val EIGHTHS = 8.0
        private const val PERCENT = 100.0

        /** D'après le taux PokéAPI : -1 pour un Pokémon asexué, sinon le nombre de huitièmes de femelles. */
        fun from(genderRate: Int): GenderRatio = when (genderRate) {
            -1 -> Genderless
            in 0..8 -> Gendered(genderRate)
            else -> throw IllegalArgumentException("Taux de femelles invalide : $genderRate")
        }
    }
}
