package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.VersionGroup
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

enum class BreedingItem(val sinnohOnly: Boolean = false) {
    NONE,
    SEA_INCENSE,
    LAX_INCENSE,
    LIGHT_BALL,
    EVERSTONE,
    ODD_INCENSE(true),
    ROCK_INCENSE(true),
    FULL_INCENSE(true),
    WAVE_INCENSE(true),
    ROSE_INCENSE(true),
    LUCK_INCENSE(true),
    PURE_INCENSE(true)
}

/** Les statistiques suivent l'ordre des tirages du moteur, pas celui de la fiche. */
enum class BreedingIv { HP, ATTACK, DEFENSE, SPEED, SPECIAL_ATTACK, SPECIAL_DEFENSE }

object GbaBreeding {
    fun babies(pair: BreedingPair, first: ParentValues, second: ParentValues): List<PokemonDetails> {
        val items = setOf(first.item, second.item)
        return pair.babies.filter { child ->
            when (child.id) {
                298 -> BreedingItem.SEA_INCENSE in items
                183 -> pair.babies.none { it.id == 298 } || BreedingItem.SEA_INCENSE !in items
                360 -> BreedingItem.LAX_INCENSE in items
                202 -> pair.babies.none { it.id == 360 } || BreedingItem.LAX_INCENSE !in items
                else -> true
            }
        }
    }

    /** Parent dont la Pierre Stase transmet la nature (0 ou 1), dans les jeux où elle la transmet. */
    fun natureParent(pair: BreedingPair, first: ParentValues, second: ParentValues, group: VersionGroup): Int? {
        if (!everstonePassesNature(group)) return null
        val parent = when {
            pair.first.id == BreedingRules.DITTO -> 0
            pair.second.id == BreedingRules.DITTO -> 1
            first.sex == ParentSex.FEMALE -> 0
            second.sex == ParentSex.FEMALE -> 1
            else -> return null
        }
        val values = if (parent == 0) first else second
        return parent.takeIf { values.item == BreedingItem.EVERSTONE }
    }

    /** La Pierre Stase transmet la nature à partir d'Émeraude ; Rouge Feu et Vert Feuille sont sortis avant. */
    private fun everstonePassesNature(group: VersionGroup): Boolean = when (group) {
        VersionGroup.HEARTGOLD_SOULSILVER -> error("Règles de reproduction hors GBA")

        VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM -> error("Règles de reproduction hors GBA")

        VersionGroup.EMERALD -> true

        VersionGroup.RED_BLUE, VersionGroup.YELLOW, VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL,
        VersionGroup.RUBY_SAPPHIRE, VersionGroup.FIRERED_LEAFGREEN -> false
    }

    fun inherited(child: PokemonDetails, donor: List<Int>, other: List<Int>, lightBall: Boolean): List<LearnedMove> =
        BreedingMoves.inherited(child, donor, other, lightBall, hatchLevel = 5)
}
