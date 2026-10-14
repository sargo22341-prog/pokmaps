package org.opensources.pokmaps.domain.map

/** Base Secrète : son entrée sur une ville ou une route, et la carte modèle de son type. */
data class SecretBase(
    val entrance: MapWarp,
    val placeId: Int,
    val placeName: String,
    val baseId: Int,
    val baseName: String
)

/**
 * Île qui se superpose à une route de la carte du monde (l'Île Mirage sur le Chenal 130) : [show] la fait
 * apparaître depuis la route, [hide] revient à la route sans elle. L'île a la taille de la carte du monde et
 * les mêmes coordonnées : ses tuiles, objets et passages se dessinent par-dessus la carte du monde.
 */
data class OverlayIsland(val islandId: Int, val worldId: Int, val routeId: Int, val show: MapWarp, val hide: MapWarp)

internal object MapPassages {
    fun secretBases(maps: Map<Int, MapInfo>, warps: Map<Int, List<MapWarp>>): List<SecretBase> =
        warps.values.flatten().filter { it.kind == WarpKind.SECRET_BASE }.map { warp ->
            val place = maps.getValue(warp.mapId)
            val base = maps.getValue(requireNotNull(warp.targetMapId) { "Base Secrète sans carte : ${warp.id}" })
            SecretBase(warp, place.id, place.name, base.id, base.name)
        }.sortedWith(compareBy({ it.placeId }, { it.entrance.y }, { it.entrance.x }))

    fun overlayIsland(maps: Map<Int, MapInfo>, warps: Map<Int, List<MapWarp>>): OverlayIsland? {
        val mirage = warps.values.flatten().filter { it.kind == WarpKind.MIRAGE }
        if (mirage.isEmpty()) return null
        val show = mirage.single { maps[it.mapId]?.parentId != null }
        val hide = mirage.single { it.mapId == show.targetMapId && it.targetMapId == show.mapId }
        val world = maps.getValue(requireNotNull(maps.getValue(show.mapId).parentId))
        val island = maps.getValue(hide.mapId)
        require(island.width == world.width && island.height == world.height && island.levelCount == world.levelCount) {
            "Île superposée de taille différente de sa carte du monde : ${island.identifier}"
        }
        return OverlayIsland(island.id, world.id, show.mapId, show, hide)
    }
}
