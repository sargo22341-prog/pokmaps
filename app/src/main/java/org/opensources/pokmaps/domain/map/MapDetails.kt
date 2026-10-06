package org.opensources.pokmaps.domain.map

import org.opensources.pokmaps.domain.pokemon.LearnedMove

/** Terrain d'un emplacement de Pokémon sauvage. */
enum class SpotKind(val identifier: String) {
    GRASS("grass"),
    WATER("water"),
    FLOOR("floor");

    companion object {
        fun from(identifier: String): SpotKind = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Terrain inconnu : $identifier"
        }
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

/** Objet du jeu (pour la recherche), avec l'attaque enseignée pour une CT / CS. */
data class ItemSummary(
    val id: Int,
    val identifier: String,
    val name: String,
    val hasSprite: Boolean,
    val moveName: String?
)

/** Nature d'une offre de personnage (colonne npc_offer.kind). */
enum class OfferKind(val identifier: String) {
    GIFT_ITEM("gift_item"),
    GIFT_POKEMON("gift_pokemon"),
    SALE("sale"),
    TRADE("trade");

    companion object {
        fun from(identifier: String): OfferKind = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Type d'offre inconnu : $identifier"
        }
    }
}

/** Don, vente ou échange d'un personnage de la carte, avec les noms des objets et des Pokémon. */
data class OfferLink(
    val objectId: Int,
    val kind: OfferKind,
    val itemIdentifier: String?,
    val itemName: String?,
    val pokemonId: Int?,
    val pokemonName: String?,
    val wantedPokemonName: String?,
    val price: Int?,
    val quantity: Int?
)

/** Objets et offres des personnages d'un jeu, parcourus par la recherche et les fiches. */
data class GameIndex(val items: List<ItemSummary>, val offers: List<OfferLink>)

/** Évolution déclenchée par un objet (pierre). */
data class ItemEvolution(val fromId: Int, val fromName: String, val toId: Int, val toName: String)

/**
 * Où trouver un Pokémon sur les cartes : `maps` (villes, routes et cartes intérieures, y compris celles des
 * personnages qui le donnent ou l'échangent) et `givers`, ces personnages.
 */
data class PokemonPlaces(val maps: Set<Int>, val givers: List<MapObject>) {
    /** On l'obtient seulement auprès de personnages : on va directement les voir. */
    val onlyFromGivers: Boolean get() = givers.isNotEmpty() && maps == givers.map { it.mapId }.toSet()
}
