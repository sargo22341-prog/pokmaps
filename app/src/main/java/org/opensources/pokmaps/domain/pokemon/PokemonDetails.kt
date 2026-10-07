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
    val traits: PokemonTraits
)

/**
 * Données des générations suivantes (voir [GenerationFeature]) : objets tenus dans la version du jeu, sexe, œufs et
 * talents. La fiche ne montre que ce que le jeu connaît.
 */
data class PokemonTraits(
    val heldItems: List<HeldItem>,
    val gender: GenderRatio,
    val eggGroups: List<String>,
    val hatchCycles: Int,
    val abilities: List<PokemonAbility>
)

/** Objet que tient un Pokémon sauvage, avec sa probabilité (%). */
data class HeldItem(val identifier: String, val name: String, val hasSprite: Boolean, val rarity: Int)

/** Talent d'un Pokémon : emplacement 1 ou 2, ou talent caché. */
data class PokemonAbility(val name: String, val description: String?, val hidden: Boolean)

data class BaseStat(val identifier: String, val name: String, val value: Int) {
    companion object {
        const val MAX = 255
    }
}

data class TypeMatchup(val type: PokemonType, val factor: Int)

/** CT ou CS d'un jeu : identifiant de l'objet (« tm01 ») et nom affiché (« CT01 »). */
data class Machine(val identifier: String, val name: String) {
    val isHm: Boolean get() = identifier.startsWith(HM_PREFIX)

    private companion object {
        const val HM_PREFIX = "hm"
    }
}

/** Attaque apprise : par niveau (`level`) ou par CT/CS (`machine`). */
data class LearnedMove(
    val moveId: Int,
    val name: String,
    val type: PokemonType,
    val damageClass: DamageClass,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    val level: Int = 0,
    val machine: Machine? = null
)

enum class DamageClass {
    PHYSICAL,
    SPECIAL,
    STATUS;

    companion object {
        fun from(identifier: String): DamageClass = when (identifier) {
            "physical" -> PHYSICAL
            "special" -> SPECIAL
            "status" -> STATUS
            else -> throw IllegalArgumentException("Catégorie d'attaque inconnue : $identifier")
        }
    }
}
