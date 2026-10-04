package org.opensources.pokmaps.domain

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.TypeChart

class TypeChartTest {
    private val normal = PokemonType(1, "normal", "Normal")
    private val fighting = PokemonType(2, "fighting", "Combat")
    private val poison = PokemonType(4, "poison", "Poison")
    private val ground = PokemonType(5, "ground", "Sol")
    private val bug = PokemonType(7, "bug", "Insecte")
    private val ghost = PokemonType(8, "ghost", "Spectre")
    private val psychic = PokemonType(14, "psychic", "Psy")
    private val types = listOf(normal, fighting, poison, ground, bug, ghost, psychic)

    // Extrait de la table de la 1re génération (Spectre sans effet sur Psy).
    private val factors = mapOf(
        (normal.id to ghost.id) to 0,
        (fighting.id to ghost.id) to 0,
        (fighting.id to poison.id) to 50,
        (poison.id to ghost.id) to 50,
        (poison.id to poison.id) to 50,
        (bug.id to ghost.id) to 50,
        (bug.id to poison.id) to 200,
        (ghost.id to ghost.id) to 200,
        (ghost.id to psychic.id) to 0,
        (ground.id to poison.id) to 200,
        (psychic.id to poison.id) to 200
    )

    @Test
    fun multipliesFactorsOfBothTypes() {
        // Ectoplasma (Spectre / Poison) en 1re génération
        val matchups = TypeChart.defensive(types, listOf(ghost.id, poison.id), factors)
            .associate { it.type.identifier to it.factor }
        assertEquals(
            mapOf("ground" to 200, "psychic" to 200, "ghost" to 200, "poison" to 25, "normal" to 0, "fighting" to 0),
            matchups
        )
    }

    @Test
    fun sortedFromWeakestToImmune() {
        val factorsOnly = TypeChart.defensive(types, listOf(ghost.id, poison.id), factors).map { it.factor }
        assertEquals(factorsOnly.sortedDescending(), factorsOnly)
    }
}
