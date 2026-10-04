package org.opensources.pokmaps.domain.pokemon

import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.PokemonType

/** Fiche complète d'un Pokémon dans le jeu choisi. */
data class PokemonDetails(
    val id: Int,
    val number: Int?,
    val name: String,
    val nameEn: String,
    val genus: String,
    val description: String?,
    val heightDm: Int,
    val weightHg: Int,
    val captureRate: Int,
    val growthRate: String,
    val types: List<PokemonType>,
    val stats: List<BaseStat>,
    /** Multiplicateur de dégâts (en %) de chaque type attaquant, sans les dégâts normaux (100 %). */
    val weaknesses: List<TypeMatchup>,
    val evolutions: List<EvolutionNode>,
    val levelUpMoves: List<LearnedMove>,
    val machineMoves: List<LearnedMove>,
    val encounters: List<Encounter>,
    /** Pokémon fixes (Ronflex, oiseaux légendaires…) placés sur les cartes du jeu. */
    val staticEncounters: Int,
    /** Sprite du jeu dans les assets, null si absent. */
    val spritePath: String?,
    val iconPath: String
)

data class BaseStat(val identifier: String, val name: String, val value: Int) {
    companion object {
        const val MAX = 255
    }
}

data class TypeMatchup(val type: PokemonType, val factor: Int)

/** Attaque apprise : par niveau (`level`) ou par CT/CS (`machine`, ex. « CT01 »). */
data class LearnedMove(
    val moveId: Int,
    val name: String,
    val type: PokemonType,
    val damageClass: DamageClass,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    val level: Int = 0,
    val machine: String? = null
)

enum class DamageClass {
    PHYSICAL,
    SPECIAL,
    STATUS;

    companion object {
        fun from(identifier: String): DamageClass = when (identifier) {
            "physical" -> PHYSICAL
            "special" -> SPECIAL
            else -> STATUS
        }
    }
}
