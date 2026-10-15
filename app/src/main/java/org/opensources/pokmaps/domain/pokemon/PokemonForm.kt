package org.opensources.pokmaps.domain.pokemon

/** Forme disponible dans une cartouche, validée à la lecture du catalogue embarqué. */
data class PokemonForm(
    val pokemonId: Int,
    val identifier: String,
    val name: String,
    val folder: String,
    val spriteIdentifier: String,
    val isDefault: Boolean,
    val baseStats: Map<String, Int>
) {
    init {
        require(pokemonId > 0 && identifier.isNotBlank() && name.isNotBlank())
        require(folder.matches(PATH_COMPONENT) && spriteIdentifier.matches(PATH_COMPONENT))
        require(baseStats.keys == STAT_IDENTIFIERS && baseStats.values.all { it in 1..BaseStat.MAX })
    }

    fun sprite(animated: Boolean, shiny: Boolean): String {
        val style = if (shiny) "shiny/" else ""
        val motion = if (animated) "animated" else "static"
        return "sprites/$folder/$style$motion/$spriteIdentifier.webp"
    }

    fun stats(original: List<BaseStat>): List<BaseStat> = original.map {
        it.copy(value = baseStats.getValue(it.identifier))
    }

    private companion object {
        val PATH_COMPONENT = Regex("[a-z0-9-]+")
        val STAT_IDENTIFIERS = setOf("hp", "attack", "defense", "special-attack", "special-defense", "speed")
    }
}
