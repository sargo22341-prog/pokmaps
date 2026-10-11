package org.opensources.pokmaps.domain.pokemon

/** Formes montrées sur la fiche ; Deoxys conserve la forme imposée par la version. */
enum class PokemonForm(val folder: String, val identifier: String) {
    CASTFORM_NORMAL("pokemon", "351"),
    CASTFORM_SUNNY("castform", "sunny"),
    CASTFORM_RAINY("castform", "rainy"),
    CASTFORM_SNOWY("castform", "snowy"),
    DEOXYS_NORMAL("pokemon", "386"),
    DEOXYS_ATTACK("deoxys", "attack"),
    DEOXYS_DEFENSE("deoxys", "defense"),
    DEOXYS_SPEED("deoxys", "speed");

    fun sprite(animated: Boolean, shiny: Boolean): String {
        val style = if (shiny) "shiny/" else ""
        val motion = if (animated) "animated" else "static"
        return "sprites/$folder/$style$motion/$identifier.webp"
    }

    /** Valeurs des formes dans la PokéAPI épinglée ; la base conserve celles de la forme Normale. */
    fun stats(original: List<BaseStat>): List<BaseStat> {
        val values = when (this) {
            CASTFORM_NORMAL, CASTFORM_SUNNY, CASTFORM_RAINY, CASTFORM_SNOWY, DEOXYS_NORMAL -> return original
            DEOXYS_ATTACK -> listOf(50, 180, 20, 180, 20, 150)
            DEOXYS_DEFENSE -> listOf(50, 70, 160, 70, 160, 90)
            DEOXYS_SPEED -> listOf(50, 95, 90, 95, 90, 180)
        }
        val identifiers = listOf("hp", "attack", "defense", "special-attack", "special-defense", "speed")
        val stats = identifiers.zip(values).toMap()
        return original.map { it.copy(value = stats.getValue(it.identifier)) }
    }

    companion object {
        fun available(pokemonId: Int, version: String): List<PokemonForm> = when (pokemonId) {
            351 -> listOf(CASTFORM_NORMAL, CASTFORM_SUNNY, CASTFORM_RAINY, CASTFORM_SNOWY)
            386 -> listOf(deoxys(version))
            else -> emptyList()
        }

        fun deoxys(version: String): PokemonForm = when (version) {
            "emerald" -> DEOXYS_SPEED
            "firered" -> DEOXYS_ATTACK
            "leafgreen" -> DEOXYS_DEFENSE
            else -> DEOXYS_NORMAL
        }
    }
}
