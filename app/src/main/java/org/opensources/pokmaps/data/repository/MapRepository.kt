package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.MapEntity
import org.opensources.pokmaps.data.db.NpcOfferRow
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
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.SpotKind
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove

@Singleton
class MapRepository @Inject constructor(private val dao: MapDao) {
    private val mutex = Mutex()
    private val catalogs = mutableMapOf<Int, MapCatalog>()
    private val indexes = mutableMapOf<Int, GameIndex>()

    /** Cartes du jeu avec leurs warps, objets et zones (gardées en mémoire : la base ne change pas). */
    suspend fun catalog(game: Game): MapCatalog = mutex.withLock {
        catalogs.getOrPut(game.versionGroupId) { loadCatalog(game) }
    }

    private suspend fun loadCatalog(game: Game): MapCatalog {
        val vg = game.versionGroupId
        return MapCatalog(
            versionGroupIdentifier = game.versionGroupIdentifier,
            maps = dao.maps(vg).map { it.toInfo() }.associateBy { it.id },
            warps = dao.warps(vg)
                .map { MapWarp(it.id, it.mapId, it.x, it.y, it.targetMapId, it.targetX, it.targetY) }
                .groupBy { it.mapId },
            objects = dao.objects(vg).map {
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
                    trainerClass = it.trainerClass
                )
            }.groupBy { it.mapId },
            areas = dao.areas(vg).map { MapArea(it.mapId, it.areaId, it.name) }.groupBy { it.mapId },
            spots = dao.spots(vg).mapNotNull { spot ->
                SpotKind.from(spot.kind)?.let { MapSpot(spot.mapId, it, spot.x, spot.y) }
            }.groupBy { it.mapId }
        )
    }

    /** Objets et offres des personnages du jeu (gardés en mémoire comme les cartes). */
    suspend fun index(game: Game): GameIndex = mutex.withLock {
        indexes.getOrPut(game.versionGroupId) {
            val vg = game.versionGroupId
            GameIndex(
                items = dao.items(vg).map { ItemSummary(it.id, it.identifier, it.name, it.hasSprite, it.moveName) },
                offers = dao.offerLinks(vg).map {
                    OfferLink(
                        objectId = it.objectId,
                        kind = it.kind,
                        itemIdentifier = it.itemIdentifier,
                        itemName = it.itemName,
                        pokemonId = it.pokemonId,
                        pokemonName = it.pokemonName,
                        wantedPokemonName = it.wantedPokemonName,
                        price = it.price,
                        quantity = it.quantity
                    )
                }
            )
        }
    }

    private fun MapEntity.toInfo() = MapInfo(id, identifier, nameFr, parentMapId, x, y, width, height, levelCount)

    /** Rencontres des zones dans la version du jeu. */
    suspend fun encounters(game: Game, areaIds: List<Int>): List<Encounter> =
        if (areaIds.isEmpty()) emptyList() else dao.encounters(game.versionId, areaIds).map { it.toEncounter() }

    /** Zones où l'on rencontre un Pokémon dans la version du jeu, avec la méthode de rencontre. */
    suspend fun pokemonAreaMethods(game: Game, pokemonId: Int): List<Pair<Int, String>> =
        dao.pokemonAreaMethods(game.versionId, pokemonId).map { it.areaId to it.method }

    /** Personnages qui donnent ou échangent un Pokémon. */
    suspend fun pokemonGivers(game: Game, pokemonId: Int): List<Int> = dao.pokemonGivers(game.versionGroupId, pokemonId)

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

    /** Dons, ventes et échanges d'un personnage. */
    suspend fun offers(objectId: Int): List<NpcOffer> = dao.offers(objectId).mapNotNull { it.toOffer() }

    private fun NpcOfferRow.toOffer(): NpcOffer? {
        val item = if (itemId != null && itemIdentifier != null && itemName != null) {
            OfferItem(itemId, itemIdentifier, itemName, itemHasSprite == true)
        } else {
            null
        }
        return when (kind) {
            "gift_item" -> item?.let { NpcOffer.GiftItem(it, quantity ?: 1) }

            "sale" -> item?.let { NpcOffer.Sale(it, price) }

            "gift_pokemon" -> if (pokemonId != null && pokemonName != null) {
                NpcOffer.GiftPokemon(pokemonId, pokemonName, quantity)
            } else {
                null
            }

            "trade" -> if (pokemonId != null && pokemonName != null && wantedPokemonId != null &&
                wantedPokemonName != null
            ) {
                NpcOffer.Trade(pokemonId, pokemonName, wantedPokemonId, wantedPokemonName)
            } else {
                null
            }

            else -> null
        }
    }

    /** Description d'un objet, ou attaque de la CT / CS dans le jeu. */
    suspend fun item(game: Game, itemId: Int): ItemDetails? = dao.item(itemId, game.versionGroupId)?.let { row ->
        val move = if (row.moveName != null && row.typeId != null && row.typeIdentifier != null &&
            row.typeName != null && row.pp != null && row.damageClass != null
        ) {
            LearnedMove(
                moveId = 0,
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
        ItemDetails(row.id, row.identifier, row.name, row.hasSprite, row.description, move)
    }
}
