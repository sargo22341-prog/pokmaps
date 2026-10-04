package org.opensources.pokmaps.domain.map

import org.opensources.pokmaps.domain.pokemon.LearnedMove

/** Terrain d'un emplacement de Pokémon sauvage. */
enum class SpotKind(val identifier: String) {
    GRASS("grass"),
    WATER("water"),
    FLOOR("floor");

    companion object {
        fun from(identifier: String): SpotKind? = entries.firstOrNull { it.identifier == identifier }
    }
}

/** Emplacement où dessiner un Pokémon sauvage (centre d'une case, en pixels de la carte affichée). */
data class MapSpot(val mapId: Int, val kind: SpotKind, val x: Int, val y: Int)

/** Pokémon de l'équipe d'un dresseur, avec les attaques qu'il utilise en combat. */
data class TrainerPokemon(val pokemonId: Int, val name: String, val level: Int, val moves: List<LearnedMove>)

/** Ce que propose un personnage quand on lui parle. */
sealed interface NpcOffer {
    data class GiftItem(val item: OfferItem, val quantity: Int) : NpcOffer

    data class Sale(val item: OfferItem, val price: Int?) : NpcOffer

    data class GiftPokemon(val pokemonId: Int, val name: String, val level: Int?) : NpcOffer

    data class Trade(val pokemonId: Int, val name: String, val wantedId: Int, val wantedName: String) : NpcOffer
}

data class OfferItem(val id: Int, val identifier: String, val name: String, val hasSprite: Boolean)

/** Objet : description, ou attaque enseignée par une CT / CS. */
data class ItemDetails(
    val id: Int,
    val identifier: String,
    val name: String,
    val hasSprite: Boolean,
    val description: String?,
    val move: LearnedMove?
)
