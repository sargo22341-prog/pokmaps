package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.map.GameIndex
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.ItemEvolution
import org.opensources.pokmaps.domain.map.ItemSummary
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry

/** Tout ce que parcourt la recherche globale dans le jeu choisi. */
data class SearchIndex(val game: Game, val pokedex: List<PokedexEntry>, val catalog: MapCatalog, val index: GameIndex)

class ObserveSearchIndexUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository,
    private val maps: MapRepository
) {
    operator fun invoke(): Flow<SearchIndex> = games.selectedGame.map {
        SearchIndex(it, pokedex.pokedex(it), maps.catalog(it), maps.index(it))
    }
}

/** Objet ou personnage de la carte lié à un objet, avec le nom de sa carte (et le prix ou la quantité). */
data class ItemSource(val obj: MapObject, val mapName: String, val price: Int? = null, val quantity: Int? = null)

/** Fiche d'un objet : où le trouver, l'acheter ou le recevoir, et sur quels Pokémon l'utiliser. */
data class ItemPage(
    val game: Game,
    val item: ItemSummary,
    val details: ItemDetails?,
    /** Objets ramassables et cachés. */
    val found: List<ItemSource>,
    val sold: List<ItemSource>,
    val given: List<ItemSource>,
    val evolutions: List<ItemEvolution>
)

class ObserveItemPageUseCase @Inject constructor(private val games: GameRepository, private val maps: MapRepository) {
    /** Fiche de l'objet dans le jeu choisi, null s'il n'y existe pas. */
    operator fun invoke(identifier: String): Flow<ItemPage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val index = maps.index(game)
        val item = index.items.firstOrNull { it.identifier == identifier } ?: return@map null
        fun MapObject.source(price: Int? = null, quantity: Int? = null) =
            ItemSource(this, catalog.maps[mapId]?.name.orEmpty(), price, quantity)

        val offers = index.offers.filter { it.itemIdentifier == identifier }
        fun offered(kind: OfferKind) = offers.filter { it.kind == kind }.mapNotNull { offer ->
            catalog.objectsById[offer.objectId]?.source(offer.price, offer.quantity)
        }.distinctBy { it.obj.id }
        ItemPage(
            game = game,
            item = item,
            details = maps.item(game, item.id),
            found = catalog.objectsById.values
                .filter { it.itemId == item.id && it.kind in FOUND_KINDS }
                .sortedBy { it.id }
                .map { it.source() },
            sold = offered(OfferKind.SALE),
            given = offered(OfferKind.GIFT_ITEM),
            evolutions = maps.itemEvolutions(game, item.id)
        )
    }

    private companion object {
        val FOUND_KINDS = setOf(MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM)
    }
}

/** Fiche d'un lieu : Pokémon sauvages, objets, personnages et lieux accessibles. */
data class PlacePage(
    val game: Game,
    val map: MapInfo,
    val encounters: List<Encounter>,
    val items: List<MapObject>,
    /** Dresseurs, Pokémon fixes et personnages qui donnent, vendent ou échangent quelque chose. */
    val characters: List<MapObject>,
    val offers: Map<Int, List<OfferLink>>,
    val places: List<MapInfo>
)

class ObservePlacePageUseCase @Inject constructor(private val games: GameRepository, private val maps: MapRepository) {
    /** Fiche du lieu dans le jeu choisi (d'après l'identifiant de sa carte), null s'il n'y existe pas. */
    operator fun invoke(identifier: String): Flow<PlacePage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val map = catalog.mapByIdentifier(identifier) ?: return@map null
        val objects = catalog.objects[map.id].orEmpty()
        val offers = maps.index(game).offers.groupBy { it.objectId }.filterKeys { id -> objects.any { it.id == id } }
        PlacePage(
            game = game,
            map = map,
            encounters = maps.encounters(game, catalog.areas[map.id].orEmpty().map { it.areaId }),
            items = objects.filter { it.kind == MapObjectKind.ITEM || it.kind == MapObjectKind.HIDDEN_ITEM },
            characters = objects.filter {
                it.kind == MapObjectKind.TRAINER || it.kind == MapObjectKind.POKEMON || it.id in offers
            },
            offers = offers,
            places = catalog.accessibleFrom(map.id).mapNotNull { warp -> warp.targetMapId?.let { catalog.maps[it] } }
        )
    }
}

/** Fiche d'un personnage ou d'un dresseur. */
data class CharacterPage(
    val game: Game,
    val obj: MapObject,
    val map: MapInfo,
    val party: List<TrainerPokemon>,
    val offers: List<NpcOffer>
)

class ObserveCharacterPageUseCase @Inject constructor(
    private val games: GameRepository,
    private val maps: MapRepository
) {
    /** Fiche du personnage (identifiant propre à la série de cartes du jeu), null s'il n'est pas dans ce jeu. */
    operator fun invoke(objectId: Int): Flow<CharacterPage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val obj = catalog.objectsById[objectId] ?: return@map null
        val map = catalog.maps[obj.mapId] ?: return@map null
        val party = if (obj.kind == MapObjectKind.TRAINER) maps.trainerParty(game, obj.id) else emptyList()
        CharacterPage(game, obj, map, party, maps.offers(obj.id))
    }
}
