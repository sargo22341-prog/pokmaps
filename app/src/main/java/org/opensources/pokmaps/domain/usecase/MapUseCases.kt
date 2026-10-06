package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.map.MapTiles
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.settings.MapSettings
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.PokemonPlaces
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import ovh.plrapps.mapcompose.core.TileStreamProvider

/** Cartes du jeu choisi. */
data class GameMaps(val game: Game, val catalog: MapCatalog)

class ObserveMapCatalogUseCase @Inject constructor(private val games: GameRepository, private val maps: MapRepository) {
    operator fun invoke(): Flow<GameMaps> = games.selectedGame.map { GameMaps(it, maps.catalog(it)) }
}

/** Rencontres d'une carte (ville, route ou carte intérieure) dans la version du jeu. */
class GetMapEncountersUseCase @Inject constructor(private val maps: MapRepository) {
    suspend operator fun invoke(game: Game, catalog: MapCatalog, mapId: Int): List<Encounter> =
        maps.encounters(game, catalog.areas[mapId].orEmpty().map { it.areaId })
}

/**
 * Cartes où l'on trouve un Pokémon dans la version du jeu : zones de rencontre, Pokémon fixes et personnages
 * qui le donnent ou l'échangent. Pour un don ou un échange, c'est le personnage qui compte (dans sa maison),
 * pas la zone de rencontre PokéAPI (souvent la route voisine).
 */
class GetPokemonMapsUseCase @Inject constructor(private val maps: MapRepository) {
    suspend operator fun invoke(game: Game, catalog: MapCatalog, pokemonId: Int): PokemonPlaces {
        val givers = maps.pokemonGivers(game, pokemonId).mapNotNull { catalog.objectsById[it] }
        val areas = maps.pokemonAreaMethods(game, pokemonId)
            .filter { (_, method) -> givers.isEmpty() || method !in NPC_METHODS }
            .map { it.first }
            .toSet()
        val byArea = catalog.areas.values.flatten().filter { it.areaId in areas }.map { it.mapId }
        val byObject = catalog.objects.values.flatten()
            .filter { it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId }
            .map { it.mapId }
        return PokemonPlaces((byArea + byObject + givers.map { it.mapId }).toSet(), givers)
    }

    private companion object {
        val NPC_METHODS = setOf("gift", "npc-trade")
    }
}

/** Ce qu'on apprend en touchant un objet ou un personnage de la carte. */
class GetMapObjectDetailsUseCase @Inject constructor(private val maps: MapRepository) {
    suspend fun trainerParty(game: Game, objectId: Int): List<TrainerPokemon> = maps.trainerParty(game, objectId)

    suspend fun offers(objectId: Int): List<NpcOffer> = maps.offers(objectId)

    suspend fun item(game: Game, itemId: Int): ItemDetails? = maps.item(game, itemId)
}

/** Tuiles d'une carte affichable, lues dans les assets. */
class GetMapTilesUseCase @Inject constructor(private val tiles: MapTiles) {
    operator fun invoke(map: GameMap): TileStreamProvider = tiles.provider(map)
}

/** Filtres de la carte choisis par l'utilisateur (tous affichés par défaut). */
class MapLayersUseCase @Inject constructor(private val settings: MapSettings) {
    val layers: Flow<Set<MapLayer>> = settings.layers.map { names ->
        names?.mapNotNull { name -> MapLayer.entries.firstOrNull { it.name == name } }?.toSet()
            ?: MapLayer.entries.toSet()
    }

    suspend fun set(layers: Set<MapLayer>) = settings.setLayers(layers.map { it.name }.toSet())
}
