package org.opensources.pokmaps.domain.pokemon

import org.opensources.pokmaps.domain.model.PokemonType

/** Ce que fait une attaque dans le jeu, et la probabilité (%) de son effet (null s'il est systématique). */
data class MoveEffect(val description: String, val chance: Double?)

/** Fiche d'une attaque dans le jeu choisi : caractéristiques, effet et CT / CS qui l'enseigne. */
data class MoveDetails(
    val id: Int,
    val name: String,
    val type: PokemonType,
    val damageClass: DamageClass,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    val effect: MoveEffect,
    val machine: Machine?
)
