package org.opensources.pokmaps.domain.map

/** Destinations du menu : régions principales et entrées des îles distribuées par événement. */
internal object MapDestinations {
    private val eventEntrances = listOf(
        "southern-island-exterior",
        "birth-island-exterior",
        "navel-rock-exterior",
        "faraway-island-entrance"
    )

    fun startRegion(group: String): String = when (group) {
        "gold-silver", "crystal" -> "johto"
        "ruby-sapphire", "emerald" -> "hoenn"
        else -> "kanto"
    }

    fun menu(worlds: List<MapInfo>, maps: Collection<MapInfo>): List<MapInfo> =
        worlds.filter { it.identifier != "hoenn-underwater" }.sortedBy { it.identifier == "sevii" } +
            eventEntrances.mapNotNull { identifier ->
                maps.firstOrNull { it.identifier == identifier && it.isDisplayable }?.let {
                    it.copy(name = it.name.substringBefore(" (").substringBefore(" —"))
                }
            }

    fun eventOf(map: MapInfo?, destinations: List<MapInfo>): MapInfo? {
        if (map == null || !map.isExternalEvent) return null
        return destinations.firstOrNull { destination ->
            destination.isExternalEvent &&
                map.identifier.startsWith("${destination.identifier.substringBeforeLast('-')}-")
        }
    }
}
