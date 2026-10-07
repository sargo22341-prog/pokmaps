package org.opensources.pokmaps.domain.pokedex

import org.opensources.pokmaps.domain.model.Game

/**
 * Portée des captures (réglage) : un Pokémon capturé compte pour le jeu choisi seulement, pour tous les jeux de sa
 * génération, ou pour tous les jeux. Chaque capture reste mémorisée dans la version où elle a été cochée : changer
 * de portée ne perd ni ne déplace rien.
 */
enum class CaptureScope(val identifier: String) {
    GAME("game"),
    GENERATION("generation"),
    ALL("all");

    /**
     * Versions dont les captures comptent pour `game` : `games` sont les jeux de l'application, `recorded` les
     * versions où des captures sont mémorisées (y compris celles d'un jeu qui n'existerait plus).
     */
    fun versionsFor(game: Game, games: List<Game>, recorded: Set<Int>): Set<Int> = when (this) {
        GAME -> setOf(game.versionId)

        GENERATION -> games.filter { it.generationId == game.generationId }.map { it.versionId }.toSet() +
            game.versionId

        ALL -> games.map { it.versionId }.toSet() + recorded + game.versionId
    }

    /** Pokémon capturés pour `game`, d'après les captures de chaque version (`caughtByVersion`). */
    fun caught(game: Game, games: List<Game>, caughtByVersion: Map<Int, Set<Int>>): Set<Int> =
        versionsFor(game, games, caughtByVersion.keys).flatMapTo(mutableSetOf()) { caughtByVersion[it].orEmpty() }

    companion object {
        val DEFAULT = GAME

        /** Portée d'après son identifiant mémorisé, null s'il est inconnu (réglage d'une autre version). */
        fun fromIdentifier(identifier: String): CaptureScope? = entries.firstOrNull { it.identifier == identifier }
    }
}
