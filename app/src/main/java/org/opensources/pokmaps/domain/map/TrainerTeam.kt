package org.opensources.pokmaps.domain.map

/** Ce qui choisit l'équipe d'un dresseur qui en a plusieurs. */
enum class TeamVariantKind(val identifier: String) {
    /** Pokémon de départ du joueur : le rival de Rouge et Bleu prend celui qui le bat. */
    PLAYER_STARTER("player-starter"),

    /** Évolution finale de l'Évoli du rival de Jaune, fixée par les deux premiers combats. */
    RIVAL_EVOLUTION("rival-evolution");

    companion object {
        fun from(identifier: String): TeamVariantKind =
            requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
                "Variante d'équipe inconnue : $identifier"
            }
    }
}

/** Variante de la partie qui donne une équipe : son genre et le Pokémon qui la nomme. */
data class TeamVariant(val kind: TeamVariantKind, val pokemonId: Int, val pokemonName: String)

/** Une équipe d'un dresseur ; `variant` est nul quand le dresseur n'en a qu'une. */
data class TrainerTeam(val variant: TeamVariant?, val members: List<TrainerPokemon>)
