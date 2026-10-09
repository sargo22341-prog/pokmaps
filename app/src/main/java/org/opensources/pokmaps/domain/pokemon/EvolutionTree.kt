package org.opensources.pokmaps.domain.pokemon

/** Condition d'une évolution : niveau, objet (pierre), échange, bonheur, beauté, statistiques… */
data class EvolutionCondition(
    val trigger: EvolutionTrigger,
    val minLevel: Int? = null,
    val itemName: String? = null,
    val itemIdentifier: String? = null,
    val itemHasSprite: Boolean = false,
    val minHappiness: Int? = null,
    val timeOfDay: String? = null,
    val minBeauty: Int? = null,
    val relativeStats: RelativeStats? = null,
    /** Probabilité (%) fixée par la personnalité du Pokémon (Chenipotte). */
    val personalityChance: Int? = null
)

/** Déclencheur d'une évolution (`evolution.trigger`) ; un déclencheur inconnu est une erreur. */
enum class EvolutionTrigger(val identifier: String) {
    LEVEL_UP("level-up"),
    TRADE("trade"),
    USE_ITEM("use-item"),

    /** Munja : il apparaît quand Ningale évolue, si l'équipe a une place libre et le Sac une Poké Ball. */
    SHED("shed");

    companion object {
        fun from(identifier: String): EvolutionTrigger = entries.firstOrNull { it.identifier == identifier }
            ?: error("Déclencheur d'évolution inconnu : $identifier")
    }
}

/** Attaque comparée à la Défense au moment d'évoluer (Debugant). */
enum class RelativeStats(val value: Int) {
    ATTACK_HIGHER(1),
    EQUAL(0),
    DEFENSE_HIGHER(-1);

    companion object {
        fun from(value: Int): RelativeStats =
            entries.firstOrNull { it.value == value } ?: error("Comparaison de statistiques inconnue : $value")
    }
}

/** Pokémon d'une famille d'évolution, avec la condition pour l'obtenir (null pour le Pokémon de base). */
data class EvolutionNode(
    val pokemonId: Int,
    val name: String,
    val condition: EvolutionCondition?,
    val children: List<EvolutionNode>
)

data class EvolutionEdge(val fromId: Int, val toId: Int, val condition: EvolutionCondition)

object EvolutionTree {
    /**
     * Arbres d'évolution d'une famille, à partir de ses membres (id → nom) et des évolutions valables dans le jeu.
     * Les racines sont les membres sans pré-évolution dans le jeu (Pikachu en 1re génération, sans Pichu).
     */
    fun build(members: Map<Int, String>, edges: List<EvolutionEdge>): List<EvolutionNode> {
        val validEdges = edges.filter { it.fromId in members && it.toId in members }
        val evolved = validEdges.map { it.toId }.toSet()
        val byParent = validEdges.groupBy { it.fromId }

        fun node(id: Int, condition: EvolutionCondition?, seen: Set<Int>): EvolutionNode = EvolutionNode(
            pokemonId = id,
            name = members.getValue(id),
            condition = condition,
            children = byParent[id].orEmpty()
                .filter { it.toId !in seen }
                .sortedBy { it.toId }
                .map { node(it.toId, it.condition, seen + it.toId) }
        )

        return members.keys.filter { it !in evolved }.sorted().map { node(it, null, setOf(it)) }
    }
}
