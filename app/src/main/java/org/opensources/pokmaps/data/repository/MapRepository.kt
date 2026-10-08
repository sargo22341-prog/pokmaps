package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.MapEntity
import org.opensources.pokmaps.data.db.NpcOfferRow
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.GameIndex
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.ItemEvolution
import org.opensources.pokmaps.domain.map.ItemSummary
import org.opensources.pokmaps.domain.map.MapArea
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapSpot
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCondition
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.OfferKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.SpotKind
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveEffect

@Singleton
class MapRepository @Inject constructor(private val dao: MapDao) {
    private val mutex = Mutex()
    private val catalogs = mutableMapOf<Int, MapCatalog>()
    private val indexes = mutableMapOf<Int, GameIndex>()

    /**
     * Cartes du jeu avec leurs warps, objets et zones, dans la version (Ho-Oh et Lugia n'ont pas le même niveau en Or
     * et en Argent) : gardées en mémoire, la base ne change pas.
     */
    suspend fun catalog(game: Game): MapCatalog = mutex.withLock {
        catalogs.getOrPut(game.versionId) { loadCatalog(game) }
    }

    private suspend fun loadCatalog(game: Game): MapCatalog {
        val vg = game.versionGroupId
        val fruits = loadFruits(game)
        return MapCatalog(
            versionGroupIdentifier = game.versionGroupIdentifier,
            maps = dao.maps(vg).map { it.toInfo() }.associateBy { it.id },
            warps = dao.warps(vg)
                .map { MapWarp(it.id, it.mapId, it.x, it.y, it.targetMapId, it.targetX, it.targetY) }
                .groupBy { it.mapId },
            objects = dao.objects(vg, game.versionId).map {
                MapObject(
                    id = it.id,
                    mapId = it.mapId,
                    kind = MapObjectKind.from(it.kind),
                    x = it.x,
                    y = it.y,
                    sprite = it.sprite,
                    itemId = it.itemId,
                    itemIdentifier = it.itemIdentifier,
                    itemName = it.itemName,
                    pokemonId = it.pokemonId,
                    pokemonName = it.pokemonName,
                    level = it.level,
                    trainerClass = it.trainerClass,
                    name = it.name,
                    itemHasSprite = it.itemHasSprite,
                    fruit = fruits[it.id]
                )
            }.groupBy { it.mapId },
            areas = dao.areas(vg).map { MapArea(it.mapId, it.areaId, it.name) }.groupBy { it.mapId },
            spots = dao.spots(vg).map { spot ->
                MapSpot(spot.mapId, SpotKind.from(spot.kind), spot.x, spot.y)
            }.groupBy { it.mapId }
        )
    }

    private suspend fun loadFruits(game: Game): Map<Int, OfferItem> {
        val trees = dao.offerLinks(game.versionId).filter { it.kind == OfferKind.FRUIT_TREE.identifier }
        if (trees.isEmpty()) return emptyMap()
        val items = dao.items(game.versionGroupId, game.versionId).associateBy { it.identifier }
        require(trees.map { it.objectId }.distinct().size == trees.size) { "Arbre avec plusieurs fruits" }
        return trees.associate { tree ->
            val item = requireNotNull(items[tree.itemIdentifier]) { "Fruit absent : ${tree.itemIdentifier}" }
            require(item.hasSprite) { "Sprite du fruit absent : ${item.identifier}" }
            tree.objectId to OfferItem(item.id, item.identifier, item.name, item.hasSprite)
        }
    }

    /**
     * Objets et offres des personnages du jeu, dans la version (les lots du Casino diffèrent entre Rouge et Bleu) :
     * gardés en mémoire comme les cartes.
     */
    suspend fun index(game: Game): GameIndex = mutex.withLock {
        indexes.getOrPut(game.versionId) {
            GameIndex(
                items = dao.items(game.versionGroupId, game.versionId).map {
                    ItemSummary(it.id, it.identifier, it.name, it.hasSprite, it.moveName)
                },
                offers = dao.offerLinks(game.versionId).map {
                    OfferLink(
                        objectId = it.objectId,
                        kind = OfferKind.from(it.kind),
                        itemIdentifier = it.itemIdentifier,
                        itemName = it.itemName,
                        pokemonId = it.pokemonId,
                        pokemonName = it.pokemonName,
                        wantedPokemonName = it.wantedPokemonName,
                        price = it.price,
                        quantity = it.quantity,
                        wantedItemIdentifier = it.wantedItemIdentifier,
                        wantedItemName = it.wantedItemName
                    )
                }
            )
        }
    }

    private fun MapEntity.toInfo() = MapInfo(
        id, identifier, nameFr, parentMapId, x, y, width, height, levelCount, isWorld, originMapId, startMapId
    )

    /** Rencontres des zones dans la version du jeu. */
    suspend fun encounters(game: Game, areaIds: List<Int>): List<Encounter> =
        if (areaIds.isEmpty()) emptyList() else dao.encounters(game.versionId, areaIds).map { it.toEncounter() }

    /** Zones où l'on rencontre un Pokémon dans la version du jeu, avec la méthode de rencontre. */
    suspend fun pokemonAreaMethods(game: Game, pokemonId: Int): List<Pair<Int, String>> =
        dao.pokemonAreaMethods(game.versionId, pokemonId).map { it.areaId to it.method }

    /** Personnages et comptoirs qui donnent, échangent, raniment ou font gagner un Pokémon dans la version. */
    suspend fun pokemonGivers(game: Game, pokemonId: Int): List<Int> = dao.pokemonGivers(game.versionId, pokemonId)

    /** Pokémon qui évoluent grâce à un objet. */
    suspend fun itemEvolutions(game: Game, itemId: Int): List<ItemEvolution> =
        dao.itemEvolutions(game.versionGroupId, itemId).map {
            ItemEvolution(it.fromId, it.fromName, it.toId, it.toName)
        }

    /** Équipe d'un dresseur de la carte, avec ses attaques dans le jeu. */
    suspend fun trainerParty(game: Game, objectId: Int): List<TrainerPokemon> {
        val moves = dao.trainerMoves(objectId, game.versionGroupId).groupBy { it.slot }
        return dao.trainerParty(objectId).map { mon ->
            TrainerPokemon(
                pokemonId = mon.pokemonId,
                name = mon.name,
                level = mon.level,
                moves = moves[mon.slot].orEmpty().map {
                    LearnedMove(
                        moveId = it.moveId,
                        name = it.name,
                        type = PokemonType(it.typeId, it.typeIdentifier, it.typeName),
                        damageClass = DamageClass.from(it.damageClass),
                        power = it.power,
                        accuracy = it.accuracy,
                        pp = it.pp
                    )
                }
            )
        }
    }

    /** Offres d'un personnage ou d'une installation dans la version du jeu, avec ce qu'exige chacune. */
    suspend fun offers(game: Game, objectId: Int): List<NpcOffer> {
        val stories = dao.offerStories(objectId).groupBy({ it.offerId }, { it.description })
        return dao.offers(objectId, game.versionId).map { row ->
            row.toOffer(OfferCondition.fromMasks(row.timeMask, row.weekdayMask, stories[row.id].orEmpty()))
        }
    }

    /** Offre lue dans la base ; une ligne incomplète est une erreur (la base est validée à la génération). */
    private fun NpcOfferRow.toOffer(condition: OfferCondition): NpcOffer = when (OfferKind.from(kind)) {
        OfferKind.GIFT_ITEM -> NpcOffer.GiftItem(offerItem(), quantity ?: 1, condition)

        OfferKind.SALE -> NpcOffer.Sale(offerItem(), price, condition)

        OfferKind.GIFT_POKEMON ->
            NpcOffer.GiftPokemon(required(pokemonId), required(pokemonName), quantity, heldItem(), condition)

        OfferKind.GIFT_EGG ->
            NpcOffer.GiftEgg(required(pokemonId), required(pokemonName), required(quantity), condition)

        OfferKind.TRADE -> trade(condition)

        OfferKind.EXCHANGE -> NpcOffer.Exchange(offerItem(), wantedItem(), condition)

        OfferKind.PRIZE_ITEM -> NpcOffer.PrizeItem(offerItem(), required(price), condition)

        OfferKind.POINT_PRIZE -> NpcOffer.PointPrize(offerItem(), required(price), condition)

        OfferKind.PRIZE_POKEMON -> prizePokemon(condition)

        OfferKind.COIN_SALE -> NpcOffer.CoinSale(required(quantity), required(price), condition)

        OfferKind.COIN_GIFT -> NpcOffer.CoinGift(required(quantity), condition)

        OfferKind.FOSSIL -> fossilRevival(condition)

        OfferKind.FRUIT_TREE -> NpcOffer.FruitTree(offerItem(), condition)

        OfferKind.HEAL -> NpcOffer.Service(CharacterService.HEAL, condition = condition)

        OfferKind.CABLE_CLUB -> NpcOffer.Service(CharacterService.CABLE_CLUB, condition = condition)

        OfferKind.NAME_RATER -> NpcOffer.Service(CharacterService.NAME_RATER, condition = condition)

        OfferKind.DAYCARE -> NpcOffer.Service(CharacterService.DAYCARE, condition = condition)

        OfferKind.MOVE_DELETER -> NpcOffer.Service(CharacterService.MOVE_DELETER, condition = condition)

        OfferKind.GROOMING -> NpcOffer.Service(CharacterService.GROOMING, price, condition)

        OfferKind.MOVE_TUTOR -> NpcOffer.Service(CharacterService.MOVE_TUTOR, required(price), condition)
    }

    private fun NpcOfferRow.trade(condition: OfferCondition) = NpcOffer.Trade(
        required(pokemonId),
        required(pokemonName),
        required(wantedPokemonId),
        required(wantedPokemonName),
        heldItem(),
        condition
    )

    private fun NpcOfferRow.prizePokemon(condition: OfferCondition) = NpcOffer.PrizePokemon(
        required(pokemonId),
        required(pokemonName),
        required(quantity),
        required(price),
        condition
    )

    private fun NpcOfferRow.fossilRevival(condition: OfferCondition) =
        NpcOffer.FossilRevival(offerItem(), required(pokemonId), required(pokemonName), required(quantity), condition)

    private fun NpcOfferRow.offerItem() =
        OfferItem(required(itemId), required(itemIdentifier), required(itemName), itemHasSprite == true)

    /** Objet que tient le Pokémon donné ou reçu lors d'un échange, s'il en tient un. */
    private fun NpcOfferRow.heldItem(): OfferItem? = itemId?.let { offerItem() }

    private fun NpcOfferRow.wantedItem() = OfferItem(
        required(wantedItemId),
        required(wantedItemIdentifier),
        required(wantedItemName),
        wantedItemHasSprite == true
    )

    private fun <T : Any> NpcOfferRow.required(value: T?): T =
        checkNotNull(value) { "Offre $kind incomplète dans la base" }

    /** Description d'un objet, ou attaque de la CT / CS dans le jeu. */
    suspend fun item(game: Game, itemId: Int): ItemDetails? = dao.item(itemId, game.versionGroupId)?.let { row ->
        val move = if (row.moveId != null && row.moveName != null && row.typeId != null &&
            row.typeIdentifier != null && row.typeName != null && row.pp != null && row.damageClass != null
        ) {
            LearnedMove(
                moveId = row.moveId,
                name = row.moveName,
                type = PokemonType(row.typeId, row.typeIdentifier, row.typeName),
                damageClass = DamageClass.from(row.damageClass),
                power = row.power,
                accuracy = row.accuracy,
                pp = row.pp
            )
        } else {
            null
        }
        val effect = row.effect?.let { MoveEffect(it, row.effectChance) }
        ItemDetails(row.id, row.identifier, row.name, row.hasSprite, row.description, move, effect)
    }
}
