package org.opensources.pokmaps.domain.map

import org.opensources.pokmaps.domain.model.VersionGroup

/** Destinations du menu : régions principales et entrées des îles distribuées par événement. */
internal object MapDestinations {
    fun startRegion(group: VersionGroup): String = when (group) {
        VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL -> "johto"
        VersionGroup.RUBY_SAPPHIRE, VersionGroup.EMERALD -> "hoenn"
        VersionGroup.RED_BLUE, VersionGroup.YELLOW, VersionGroup.FIRERED_LEAFGREEN -> "kanto"
    }

    /** Régions, puis l'entrée de chaque île : la carte affichée qui la contient (son plan, s'il y en a un). */
    fun menu(worlds: List<MapInfo>, maps: Collection<MapInfo>): List<MapInfo> {
        val byId = maps.associateBy { it.id }
        return worlds.filter { it.identifier != "hoenn-underwater" }.sortedBy { it.identifier == "sevii" } +
            maps.filter { it.eventEntranceOrder > 0 }.sortedBy { it.eventEntranceOrder }.mapNotNull { entrance ->
                val displayed = entrance.parentId?.let(byId::get) ?: entrance
                displayed.takeIf { it.isDisplayable }
                    ?.let { it.copy(name = it.name.substringBefore(" (").substringBefore(" —")) }
            }
    }

    fun eventOf(map: MapInfo?, destinations: List<MapInfo>): MapInfo? {
        val island = map?.externalEventKey ?: return null
        return destinations.firstOrNull { it.externalEventKey == island }
    }
}
