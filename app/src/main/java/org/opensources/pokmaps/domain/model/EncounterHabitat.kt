package org.opensources.pokmaps.domain.model

/** Décor fixe d’Émeraude, choisi à partir du lieu réel et non du type du Pokémon. */
enum class EncounterHabitat(val asset: String) {
    GRASS("grass"),
    TALL_GRASS("tall_grass"),
    FOREST("forest"),
    CAVE("cave"),
    ICE("ice"),
    SAND("sand"),
    FLOOR("floor");

    companion object {
        fun of(location: String, area: String, method: String): EncounterHabitat = when {
            method.startsWith("headbutt") || method == "honey-tree" -> FOREST
            location in iceLocations || (location == "shoal-cave" && area == "b3f") -> ICE
            location == "hoenn-route-111" && method == "walk" -> SAND
            area in outdoorAreas || area.endsWith("mountainside") -> outdoor(method)
            location in caveLocations || location.endsWith("-cave") || location.endsWith("-cavern") -> CAVE
            location == "mt-ember" && area.isNotEmpty() && area != "summit" -> CAVE
            location == "iron-island" && area.isNotEmpty() -> CAVE
            location in floorLocations || location.endsWith("-tower") || location.endsWith("-chamber") -> FLOOR
            else -> outdoor(method)
        }

        private fun outdoor(method: String): EncounterHabitat = if (method == "walk") TALL_GRASS else GRASS

        private val iceLocations = setOf("ice-path", "icefall-cave", "seafoam-islands", "snowpoint-temple")
        private val outdoorAreas = setOf("outside", "summit", "exterior")
        private val caveLocations = setOf(
            "rock-tunnel", "union-cave", "digletts-cave", "cerulean-cave", "dark-cave", "dragons-den",
            "slowpoke-well", "mt-moon", "mt-mortar", "mt-silver", "whirl-islands", "rusturf-tunnel", "tohjo-falls",
            "meteor-falls", "fiery-path", "desert-underpass", "hoenn-victory-road", "kanto-victory-road-1",
            "kanto-victory-road-2", "sinnoh-victory-road", "oreburgh-gate", "oreburgh-mine", "ravaged-path",
            "mt-coronet", "stark-mountain", "maniac-tunnel", "navel-rock", "terra-cave", "marine-cave",
            "desert-ruins", "ancient-tomb", "island-cave", "magma-hideout", "team-magma-hideout"
        )
        private val floorLocations = setOf(
            "pokemon-mansion", "kanto-power-plant", "new-mauville", "abandoned-ship", "mt-pyre",
            "old-chateau", "solaceon-ruins", "ruins-of-alph", "tanoby-ruins", "team-aqua-hideout",
            "sprout-tower", "sky-pillar", "team-rocket-hq"
        )
    }
}
