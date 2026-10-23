package org.opensources.pokmaps.domain.model

/** Identité des cartouches, distincte des identifiants de stockage. */
enum class GameVersion(val id: Int, val identifier: String, val group: VersionGroup, val generation: Generation) {
    RED(1, "red", VersionGroup.RED_BLUE, Generation.GEN1),
    BLUE(2, "blue", VersionGroup.RED_BLUE, Generation.GEN1),
    YELLOW(3, "yellow", VersionGroup.YELLOW, Generation.GEN1),
    GOLD(4, "gold", VersionGroup.GOLD_SILVER, Generation.GEN2),
    SILVER(5, "silver", VersionGroup.GOLD_SILVER, Generation.GEN2),
    CRYSTAL(6, "crystal", VersionGroup.CRYSTAL, Generation.GEN2),
    RUBY(7, "ruby", VersionGroup.RUBY_SAPPHIRE, Generation.GEN3),
    SAPPHIRE(8, "sapphire", VersionGroup.RUBY_SAPPHIRE, Generation.GEN3),
    EMERALD(9, "emerald", VersionGroup.EMERALD, Generation.GEN3),
    FIRERED(10, "firered", VersionGroup.FIRERED_LEAFGREEN, Generation.GEN3),
    LEAFGREEN(11, "leafgreen", VersionGroup.FIRERED_LEAFGREEN, Generation.GEN3),
    DIAMOND(12, "diamond", VersionGroup.DIAMOND_PEARL, Generation.GEN4),
    PEARL(13, "pearl", VersionGroup.DIAMOND_PEARL, Generation.GEN4),
    PLATINUM(14, "platinum", VersionGroup.PLATINUM, Generation.GEN4),
    HEARTGOLD(15, "heartgold", VersionGroup.HEARTGOLD_SOULSILVER, Generation.GEN4),
    SOULSILVER(16, "soulsilver", VersionGroup.HEARTGOLD_SOULSILVER, Generation.GEN4);

    companion object {
        fun of(id: Int): GameVersion = requireNotNull(entries.firstOrNull { it.id == id }) {
            "Version sans règles dans l'application : $id"
        }

        fun of(identifier: String): GameVersion = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Version sans règles dans l'application : $identifier"
        }
    }
}
