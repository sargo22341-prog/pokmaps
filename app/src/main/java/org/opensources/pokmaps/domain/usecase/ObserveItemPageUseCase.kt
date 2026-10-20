package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.HoennRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.ItemEvolution
import org.opensources.pokmaps.domain.map.ItemSummary
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.OfferCurrency
import org.opensources.pokmaps.domain.map.OfferKind
import org.opensources.pokmaps.domain.map.kind
import org.opensources.pokmaps.domain.model.Game

/**
 * Objet ou personnage de la carte lié à un objet, avec le nom de sa carte, le prix et sa monnaie,
 * la quantité, et l'autre objet d'un échange.
 */
data class ItemSource(
    val obj: MapObject,
    val mapName: String,
    val price: Int? = null,
    val quantity: Int? = null,
    val otherItemName: String? = null,
    val currency: OfferCurrency = OfferCurrency.MONEY
)

/** Fiche d'un objet : où le trouver, l'acheter, le recevoir ou le gagner, et ce qu'il devient. */
data class ItemPage(
    val game: Game,
    val item: ItemSummary,
    val details: ItemDetails?,
    /** Objets ramassables et cachés. */
    val found: List<ItemSource>,
    val sold: List<ItemSource>,
    val given: List<ItemSource>,
    val evolutions: List<ItemEvolution>,
    /** Personnages qui le donnent contre un autre objet (`otherItemName` : l'objet demandé). */
    val exchangedFor: List<ItemSource> = emptyList(),
    /** Personnages qui donnent un autre objet contre celui-ci (`otherItemName` : l'objet reçu). */
    val exchangeableFor: List<ItemSource> = emptyList(),
    /** Comptoirs du Casino où on le gagne (`price` en jetons). */
    val prizes: List<ItemSource> = emptyList(),
    /** Fossile : le Pokémon qu'il devient et le personnage qui le ranime. */
    val fossil: FossilUse? = null,
    val berry: org.opensources.pokmaps.domain.hoenn.Berry? = null,
    val sinnohBerry: org.opensources.pokmaps.domain.sinnoh.SinnohBerry? = null
) {
    /** On ne peut l'obtenir nulle part sur les cartes du jeu. */
    val nowhere: Boolean get() = found.isEmpty() && sold.isEmpty() && given.isEmpty() && exchangedFor.isEmpty() &&
        prizes.isEmpty()
}

class ObserveItemPageUseCase @Inject constructor(
    private val games: GameRepository,
    private val maps: MapRepository,
    private val hoenn: HoennRepository,
    private val sinnoh: org.opensources.pokmaps.data.repository.SinnohRepository
) {
    /** Fiche de l'objet dans le jeu choisi, null s'il n'y existe pas. */
    operator fun invoke(identifier: String): Flow<ItemPage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val index = maps.index(game)
        val item = index.items.firstOrNull { it.identifier == identifier } ?: return@map null
        fun MapObject.source(
            price: Int? = null,
            quantity: Int? = null,
            other: String? = null,
            currency: OfferCurrency = OfferCurrency.MONEY
        ) = ItemSource(this, catalog.maps[mapId]?.name.orEmpty(), price, quantity, other, currency)

        fun offered(kind: OfferKind, wanted: Boolean = false) = index.offers
            .filter { it.kind == kind && (if (wanted) it.wantedItemIdentifier else it.itemIdentifier) == identifier }
            .mapNotNull { offer ->
                val other = if (wanted) offer.itemName else offer.wantedItemName
                catalog.objectsById[offer.objectId]?.source(offer.price, offer.quantity, other, offer.currency)
            }
            .distinctBy { it.obj.id to it.otherItemName }
        ItemPage(
            game = game,
            item = item,
            details = maps.item(game, item.id),
            found = catalog.objectsById.values
                .filter { it.itemId == item.id && it.kind in FOUND_KINDS }
                .sortedBy { it.id }
                .map { it.source() },
            sold = offered(OfferKind.SALE),
            given = offered(OfferKind.GIFT_ITEM) + offered(OfferKind.FRUIT_TREE),
            evolutions = maps.itemEvolutions(game, item.id),
            exchangedFor = offered(OfferKind.EXCHANGE),
            exchangeableFor = offered(OfferKind.EXCHANGE, wanted = true),
            prizes = offered(OfferKind.PRIZE_ITEM),
            fossil = FossilUse.of(index, catalog)[identifier],
            berry = hoenn.content(game)?.berries?.get(identifier),
            sinnohBerry = sinnoh.content(game)?.berries?.get(identifier)
        )
    }

    private companion object {
        val FOUND_KINDS = setOf(MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM)
    }
}
