package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveNote
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

/** Passes communes aux moteurs GBA et DS ; seul le niveau à l’éclosion diffère. */
internal object BreedingMoves {
    fun inherited(
        child: PokemonDetails,
        donor: List<Int>,
        other: List<Int>,
        lightBall: Boolean,
        hatchLevel: Int
    ): List<LearnedMove> {
        require(donor.size <= 4 && other.size <= 4)
        val egg = child.eggMoves.filter { it.note != MoveNote.LIGHT_BALL_PARENT }.map { it.moveId }.toSet()
        val machines = child.machineMoves.map { it.moveId }.toSet()
        val levels = child.levelUpMoves.map { it.moveId }.toSet()
        val available = (child.levelUpMoves + child.machineMoves + child.eggMoves).associateBy { it.moveId }
        val result = child.levelUpMoves.filter {
            it.level <= hatchLevel
        }.map { it.moveId }.distinct().takeLast(4).toMutableList()
        // Le moteur effectue trois passes : œuf, CT/CS, puis niveaux communs aux deux parents.
        val inherited = donor.filter { it in egg } + donor.filter { it in machines } +
            donor.filter { it in other && it in levels } +
            child.eggMoves.filter { lightBall && it.note == MoveNote.LIGHT_BALL_PARENT }.map { it.moveId }
        for (move in inherited) {
            if (move in result) continue
            if (result.size == 4) result.removeAt(0)
            result += move
        }
        return result.map { available.getValue(it) }
    }
}
