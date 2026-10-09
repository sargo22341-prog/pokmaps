package org.opensources.pokmaps.domain.pokemon

/** Onglet d'attaques de la fiche d'un Pokémon. */
enum class MoveTab { LEVEL_UP, MACHINE, EGG, TUTOR }

/** Précision affichée sous une attaque apprise d'une façon particulière. */
enum class MoveNote {
    /** Le parent tient un Ballon Lumière. */
    LIGHT_BALL_PARENT,

    /** Un autre jeu enseigne l'attaque. */
    EXTERNAL_EVENT
}

/**
 * Méthode d'apprentissage de la base (`pokemon_move.method`), avec l'onglet où l'attaque s'affiche. Une méthode
 * inconnue est une erreur : l'attaque ne doit pas disparaître de la fiche sans bruit.
 */
enum class LearnMethod(val identifier: String, val tab: MoveTab, val note: MoveNote?) {
    LEVEL_UP("level-up", MoveTab.LEVEL_UP, null),
    MACHINE("machine", MoveTab.MACHINE, null),
    EGG("egg", MoveTab.EGG, null),
    TUTOR("tutor", MoveTab.TUTOR, null),

    /** Électacle de Pichu, né d'un parent qui tient un Ballon Lumière (Émeraude). */
    LIGHT_BALL_EGG("light-ball-egg", MoveTab.EGG, MoveNote.LIGHT_BALL_PARENT),

    /** Surf du Pikachu Surfeur de Pokémon Stadium (Rouge, Bleu et Jaune). */
    STADIUM_SURFING_PIKACHU("stadium-surfing-pikachu", MoveTab.TUTOR, MoveNote.EXTERNAL_EVENT);

    companion object {
        fun from(identifier: String): LearnMethod = entries.firstOrNull { it.identifier == identifier }
            ?: error("Méthode d'apprentissage inconnue : $identifier")
    }
}
