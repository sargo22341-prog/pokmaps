package org.opensources.pokmaps.domain.map

/** Les deux étapes du scénario partagent un repère, tout en conservant leurs identifiants de combat. */
internal fun mergeRoute22Rival(objects: List<MapObject>, maps: Map<Int, MapInfo>, generation: Int): List<MapObject> {
    if (generation != 1) return objects
    val rivals = objects.filter {
        maps[it.mapId]?.identifier == "route-22" && it.sprite == "blue" && it.kind == MapObjectKind.TRAINER
    }.sortedBy { it.name }
    if (rivals.size != 2) return objects
    val first = rivals.first()
    return objects.mapNotNull { actor ->
        when (actor.id) {
            first.id -> actor.copy(name = actor.name.substringBefore(" ("), battleObjectIds = rivals.map { it.id })
            rivals.last().id -> null
            else -> actor
        }
    }
}
