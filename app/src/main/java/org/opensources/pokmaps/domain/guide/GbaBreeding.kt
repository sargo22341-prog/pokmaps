package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveNote
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

enum class BreedingItem { NONE, SEA_INCENSE, LAX_INCENSE, LIGHT_BALL, EVERSTONE }

/** Les statistiques suivent l'ordre des tirages du moteur, pas celui de la fiche. */
enum class BreedingIv { HP, ATTACK, DEFENSE, SPEED, SPECIAL_ATTACK, SPECIAL_DEFENSE }

object GbaBreeding {
    fun babies(pair: BreedingPair, first: ParentValues, second: ParentValues): List<PokemonDetails> {
        val items = setOf(first.item, second.item)
        return pair.babies.filter { child ->
            when (child.id) {
                298 -> BreedingItem.SEA_INCENSE in items
                183 -> pair.babies.none { it.id == 298 } || BreedingItem.SEA_INCENSE !in items
                360 -> BreedingItem.LAX_INCENSE in items
                202 -> pair.babies.none { it.id == 360 } || BreedingItem.LAX_INCENSE !in items
                else -> true
            }
        }
    }

    fun natureParent(pair: BreedingPair, first: ParentValues, second: ParentValues, emerald: Boolean): Int? {
        if (!emerald) return null
        val parent = when {
            pair.first.id == BreedingRules.DITTO -> 0
            pair.second.id == BreedingRules.DITTO -> 1
            first.sex == ParentSex.FEMALE -> 0
            second.sex == ParentSex.FEMALE -> 1
            else -> return null
        }
        val values = if (parent == 0) first else second
        return parent.takeIf { values.item == BreedingItem.EVERSTONE }
    }

    fun inherited(child: PokemonDetails, donor: List<Int>, other: List<Int>, lightBall: Boolean): List<LearnedMove> {
        require(donor.size <= 4 && other.size <= 4)
        val egg = child.eggMoves.filter { it.note != MoveNote.LIGHT_BALL_PARENT }.map { it.moveId }.toSet()
        val machines = child.machineMoves.map { it.moveId }.toSet()
        val levels = child.levelUpMoves.map { it.moveId }.toSet()
        val available = (child.levelUpMoves + child.machineMoves + child.eggMoves).associateBy { it.moveId }
        val result = child.levelUpMoves.filter {
            it.level <= 5
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
