package org.opensources.pokmaps.domain.map

/**
 * Ce que le joueur indique de sa partie pour voir la bonne équipe d'un rival qui en a plusieurs ; mémorisé par
 * groupe de versions.
 */
data class RivalChoice(
    /** Pokémon de départ du joueur, null tant qu'il ne l'a pas indiqué. */
    val starterId: Int? = null,
    /** Jaune : le joueur a battu le rival au laboratoire du Prof. Chen. */
    val wonLabBattle: Boolean = true,
    /** Jaune : le joueur a battu le rival au premier combat de la route 22 (sinon perdu ou évité). */
    val wonRoute22Battle: Boolean = true
) {
    /**
     * Jaune : évolution finale de l'Évoli du rival (scripts/OaksLab.asm et Route22.asm de pokeyellow). Aquali si
     * le joueur perd au laboratoire ; sinon Voltali s'il gagne aussi sur la route 22, Pyroli s'il y perd ou
     * évite le combat.
     */
    val rivalEvolutionId: Int
        get() = when {
            !wonLabBattle -> VAPOREON
            wonRoute22Battle -> JOLTEON
            else -> FLAREON
        }

    private companion object {
        const val VAPOREON = 134
        const val JOLTEON = 135
        const val FLAREON = 136
    }
}

/**
 * Équipes d'un dresseur selon la partie. Pour un dresseur à variantes, `variants` liste les choix possibles
 * (Pokémon de départ du joueur dans l'ordre du Pokédex, ou évolutions de l'Évoli du rival) et `selected` celle que
 * donne `choice` ; `shown` ne garde que son équipe. Un dresseur à équipe unique n'a ni variante ni choix.
 */
data class TeamSelection(
    val shown: List<TrainerTeam>,
    val variants: List<TeamVariant> = emptyList(),
    val selected: TeamVariant? = null,
    val choice: RivalChoice = RivalChoice()
) {
    val kind: TeamVariantKind? get() = selected?.kind

    /** Il n'y a aucune équipe : elle dépend de la partie sans être connue. */
    val unknown: Boolean get() = shown.isEmpty()

    companion object {
        fun of(teams: List<TrainerTeam>, choice: RivalChoice): TeamSelection {
            val variants = teams.mapNotNull { it.variant }.distinct().sortedBy { it.pokemonId }
            if (variants.isEmpty()) return TeamSelection(teams, choice = choice)
            val kind = variants.first().kind
            require(variants.all { it.kind == kind }) { "Variantes d'équipe de natures différentes : $variants" }
            val wanted = when (kind) {
                TeamVariantKind.PLAYER_STARTER -> choice.starterId
                TeamVariantKind.RIVAL_EVOLUTION -> choice.rivalEvolutionId
            }
            val selected = variants.firstOrNull { it.pokemonId == wanted } ?: variants.first()
            val shown = teams.filter { it.variant == null || it.variant == selected }
            return TeamSelection(shown, variants, selected, choice)
        }
    }
}
