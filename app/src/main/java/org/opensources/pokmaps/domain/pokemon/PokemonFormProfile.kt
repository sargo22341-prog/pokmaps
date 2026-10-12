package org.opensources.pokmaps.domain.pokemon

/** Profils de statistiques et forme imposée par la cartouche. */
internal object PokemonFormProfile {
    /** Valeurs des formes dans la PokéAPI épinglée ; la base conserve celles de la forme Normale. */
    fun stats(form: PokemonForm, original: List<BaseStat>): List<BaseStat> {
        val values = when (form) {
            PokemonForm.CASTFORM_NORMAL, PokemonForm.CASTFORM_SUNNY, PokemonForm.CASTFORM_RAINY,
            PokemonForm.CASTFORM_SNOWY, PokemonForm.DEOXYS_NORMAL -> return original

            PokemonForm.DEOXYS_ATTACK -> listOf(50, 180, 20, 180, 20, 150)

            PokemonForm.DEOXYS_DEFENSE -> listOf(50, 70, 160, 70, 160, 90)

            PokemonForm.DEOXYS_SPEED -> listOf(50, 95, 90, 95, 90, 180)
        }
        val identifiers = listOf("hp", "attack", "defense", "special-attack", "special-defense", "speed")
        val stats = identifiers.zip(values).toMap()
        return original.map { it.copy(value = stats.getValue(it.identifier)) }
    }

    fun deoxys(version: String): PokemonForm = when (version) {
        "emerald" -> PokemonForm.DEOXYS_SPEED
        "firered" -> PokemonForm.DEOXYS_ATTACK
        "leafgreen" -> PokemonForm.DEOXYS_DEFENSE
        else -> PokemonForm.DEOXYS_NORMAL
    }
}
