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

    fun stats(original: List<BaseStat>): List<BaseStat> = PokemonFormProfile.stats(this, original)

    companion object {
        fun available(pokemonId: Int, version: String): List<PokemonForm> = when (pokemonId) {
            351 -> listOf(CASTFORM_NORMAL, CASTFORM_SUNNY, CASTFORM_RAINY, CASTFORM_SNOWY)
            386 -> listOf(deoxys(version))
            else -> emptyList()
        }

        fun deoxys(version: String): PokemonForm = PokemonFormProfile.deoxys(version)
    }
}
