package org.opensources.pokmaps.domain.map

import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveEffect

/** Terrain d'un emplacement de Pokémon sauvage. */
enum class SpotKind(val identifier: String) {
    GRASS("grass"),
    WATER("water"),
    FLOOR("floor"),
    TREE("tree"),
    ROCK("rock");

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

/**
 * Ce que propose un personnage ou une installation quand on lui parle, et ce qu'exige l'offre pour être possible
 * (`condition` : moments, jours, étapes du scénario).
 */
sealed interface NpcOffer {
    val condition: OfferCondition

    data class GiftItem(
        val item: OfferItem,
        val quantity: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    data class Sale(
        val item: OfferItem,
        val price: Int?,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Pokémon donné, avec l'objet qu'il tient (2e génération : Baie Oran des Pokémon de départ). */
    data class GiftPokemon(
        val pokemonId: Int,
        val name: String,
        val level: Int?,
        val heldItem: OfferItem? = null,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Œuf donné, qui éclot au niveau `level` (Togepi de l'assistant du Prof. Orme). */
    data class GiftEgg(
        val pokemonId: Int,
        val name: String,
        val level: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Pokémon reçu contre un autre, avec l'objet qu'il tient (2e génération). */
    data class Trade(
        val pokemonId: Int,
        val name: String,
        val wantedId: Int,
        val wantedName: String,
        val heldItem: OfferItem? = null,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Objet donné contre un autre (Bicyclette contre le Bon Commande, CT contre une boisson). */
    data class Exchange(
        val item: OfferItem,
        val wanted: OfferItem,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Lot du Casino, contre des jetons. */
    data class PrizeItem(
        val item: OfferItem,
        val coins: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Récompense de Buena contre les points de la Carte Bleue. */
    data class PointPrize(
        val item: OfferItem,
        val points: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    data class PrizePokemon(
        val pokemonId: Int,
        val name: String,
        val level: Int,
        val coins: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Jetons du Casino vendus (`coins` jetons pour `price` ₽) ou donnés. */
    data class CoinSale(
        val coins: Int,
        val price: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    data class CoinGift(val coins: Int, override val condition: OfferCondition = OfferCondition.ALWAYS) : NpcOffer

    /** Fossile ranimé en Pokémon. */
    data class FossilRevival(
        val fossil: OfferItem,
        val pokemonId: Int,
        val name: String,
        val level: Int,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer

    /** Baie ou Noigrume que donne un arbre, une fois par jour. */
    data class FruitTree(val item: OfferItem, override val condition: OfferCondition = OfferCondition.ALWAYS) : NpcOffer

    /** Service rendu, gratuit ou payant (`price` en ₽ pour le toilettage, en jetons pour le tuteur). */
    data class Service(
        val service: CharacterService,
        val price: Int? = null,
        override val condition: OfferCondition = OfferCondition.ALWAYS
    ) : NpcOffer
}

/** Nature d'une offre lue dans la base. */
val NpcOffer.kind: OfferKind
    get() = when (this) {
        is NpcOffer.GiftItem -> OfferKind.GIFT_ITEM

        is NpcOffer.Sale -> OfferKind.SALE

        is NpcOffer.GiftPokemon -> OfferKind.GIFT_POKEMON

        is NpcOffer.GiftEgg -> OfferKind.GIFT_EGG

        is NpcOffer.Trade -> OfferKind.TRADE

        is NpcOffer.Exchange -> OfferKind.EXCHANGE

        is NpcOffer.PrizeItem -> OfferKind.PRIZE_ITEM

        is NpcOffer.PointPrize -> OfferKind.POINT_PRIZE

        is NpcOffer.PrizePokemon -> OfferKind.PRIZE_POKEMON

        is NpcOffer.CoinSale -> OfferKind.COIN_SALE

        is NpcOffer.CoinGift -> OfferKind.COIN_GIFT

        is NpcOffer.FossilRevival -> OfferKind.FOSSIL

        is NpcOffer.FruitTree -> OfferKind.FRUIT_TREE

        is NpcOffer.Service -> when (service) {
            CharacterService.HEAL -> OfferKind.HEAL
            CharacterService.CABLE_CLUB -> OfferKind.CABLE_CLUB
            CharacterService.NAME_RATER -> OfferKind.NAME_RATER
            CharacterService.DAYCARE -> OfferKind.DAYCARE
            CharacterService.MOVE_DELETER -> OfferKind.MOVE_DELETER
            CharacterService.GROOMING -> OfferKind.GROOMING
            CharacterService.MOVE_TUTOR -> OfferKind.MOVE_TUTOR
        }
    }

/** Service rendu par un personnage, sans objet ni Pokémon. */
enum class CharacterService {
    HEAL,
    CABLE_CLUB,
    NAME_RATER,
    DAYCARE,

    /** Effaceur de capacités : fait oublier une attaque, même une CS. */
    MOVE_DELETER,

    /** Toilettage qui rend un Pokémon plus heureux. */
    GROOMING,

    /** Tuteur de Cristal : Lance-Flammes, Tonnerre et Laser Glace, prix en jetons. */
    MOVE_TUTOR
}

data class OfferItem(val id: Int, val identifier: String, val name: String, val hasSprite: Boolean)

/** Objet : description, ou attaque enseignée par une CT / CS et ce qu'elle fait. */
data class ItemDetails(
    val id: Int,
    val identifier: String,
    val name: String,
    val hasSprite: Boolean,
    val description: String?,
    val move: LearnedMove?,
    val moveEffect: MoveEffect? = null
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
    GIFT_EGG("gift_egg"),
    SALE("sale"),
    TRADE("trade"),
    EXCHANGE("exchange"),
    PRIZE_ITEM("prize_item"),
    PRIZE_POKEMON("prize_pokemon"),
    COIN_SALE("coin_sale"),
    COIN_GIFT("coin_gift"),
    FOSSIL("fossil"),
    FRUIT_TREE("fruit_tree"),
    HEAL("heal"),
    CABLE_CLUB("cable_club"),
    NAME_RATER("name_rater"),
    DAYCARE("daycare"),
    MOVE_DELETER("move_deleter"),
    GROOMING("grooming"),
    MOVE_TUTOR("move_tutor"),
    POINT_PRIZE("point_prize");

    companion object {
        fun from(identifier: String): OfferKind = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Type d'offre inconnu : $identifier"
        }
    }
}

/** Offre d'un personnage ou d'une installation de la carte, avec les noms des objets et des Pokémon. */
data class OfferLink(
    val objectId: Int,
    val kind: OfferKind,
    val itemIdentifier: String?,
    val itemName: String?,
    val pokemonId: Int?,
    val pokemonName: String?,
    val wantedPokemonName: String?,
    val price: Int?,
    val quantity: Int?,
    val wantedItemIdentifier: String? = null,
    val wantedItemName: String? = null
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
