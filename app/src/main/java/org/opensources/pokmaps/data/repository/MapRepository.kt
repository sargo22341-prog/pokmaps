package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.MapEntity
import org.opensources.pokmaps.domain.map.MapArea
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.MapWarp
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game

@Singleton
class MapRepository @Inject constructor(private val dao: MapDao) {
    private val mutex = Mutex()
    private val catalogs = mutableMapOf<Int, MapCatalog>()

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
            areas = dao.areas(vg).map { MapArea(it.mapId, it.areaId, it.name) }.groupBy { it.mapId }
        )
    }

    private fun MapEntity.toInfo() = MapInfo(id, identifier, nameFr, parentMapId, x, y, width, height, levelCount)

    /** Rencontres des zones dans la version du jeu. */
    suspend fun encounters(game: Game, areaIds: List<Int>): List<Encounter> =
        if (areaIds.isEmpty()) emptyList() else dao.encounters(game.versionId, areaIds).map { it.toEncounter() }

    /** Zones où l'on rencontre un Pokémon dans la version du jeu. */
    suspend fun pokemonAreas(game: Game, pokemonId: Int): Set<Int> = dao.pokemonAreas(game.versionId, pokemonId).toSet()
}
