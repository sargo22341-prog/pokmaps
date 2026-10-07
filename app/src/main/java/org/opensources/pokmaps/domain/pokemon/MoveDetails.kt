package org.opensources.pokmaps.domain.pokemon

import org.opensources.pokmaps.domain.model.PokemonType

/** Ce que fait une attaque dans le jeu, et la probabilité (%) de son effet (null s'il est systématique). */
data class MoveEffect(val description: String, val chance: Double?)

/** Fiche d'une attaque dans le jeu choisi : caractéristiques, effet, CT/CS qui l'enseigne et Pokémon qui l'apprennent. */
data class MoveDetails(
    val id: Int,
    val name: String,
    val type: PokemonType,
    val damageClass: DamageClass,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    val effect: MoveEffect,
    val machine: Machine?,
    val learners: List<MoveLearner>
) {
    /** Pokémon qui l'apprennent en montant de niveau, par niveau puis par numéro. */
    val levelUpLearners: List<MoveLearner> get() = learners.filter { it.level != null }

    /** Pokémon à qui la CT / CS peut l'apprendre. */
    val machineLearners: List<MoveLearner> get() = learners.filter { it.level == null }
}

/** Pokémon qui apprend l'attaque : au niveau `level`, ou par CT/CS si `level` est null. */
data class MoveLearner(val pokemonId: Int, val name: String, val level: Int?)
