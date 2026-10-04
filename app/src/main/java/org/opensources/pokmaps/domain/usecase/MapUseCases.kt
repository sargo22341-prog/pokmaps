package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game

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

/** Cartes où l'on trouve un Pokémon dans la version du jeu : zones de rencontre et Pokémon fixes. */
class GetPokemonMapsUseCase @Inject constructor(private val maps: MapRepository) {
    suspend operator fun invoke(game: Game, catalog: MapCatalog, pokemonId: Int): Set<Int> {
        val areas = maps.pokemonAreas(game, pokemonId)
        val byArea = catalog.areas.values.flatten().filter { it.areaId in areas }.map { it.mapId }
        val byObject = catalog.objects.values.flatten()
            .filter { it.kind == MapObjectKind.POKEMON && it.pokemonId == pokemonId }
            .map { it.mapId }
        return (byArea + byObject).toSet()
    }
}
