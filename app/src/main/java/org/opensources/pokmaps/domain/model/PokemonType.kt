package org.opensources.pokmaps.domain.model

/** Type d'un Pokémon ou d'une attaque (identifiant PokéAPI, ex. « fire », nom français « Feu »). */
data class PokemonType(val id: Int, val identifier: String, val name: String)
