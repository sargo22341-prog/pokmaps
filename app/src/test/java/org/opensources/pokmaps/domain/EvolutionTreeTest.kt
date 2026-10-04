package org.opensources.pokmaps.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionEdge
import org.opensources.pokmaps.domain.pokemon.EvolutionTree

class EvolutionTreeTest {
    @Test
    fun branchingEvolutions() {
        val stone = { name: String -> EvolutionCondition("use-item", itemName = name) }
        val trees = EvolutionTree.build(
            members = mapOf(133 to "Évoli", 134 to "Aquali", 135 to "Voltali", 136 to "Pyroli"),
            edges = listOf(
                EvolutionEdge(133, 136, stone("Pierre Feu")),
                EvolutionEdge(133, 134, stone("Pierre Eau")),
                EvolutionEdge(133, 135, stone("Pierre Foudre"))
            )
        )
        val eevee = trees.single()
        assertNull(eevee.condition)
        assertEquals(listOf(134, 135, 136), eevee.children.map { it.pokemonId })
        assertEquals("Pierre Eau", eevee.children.first().condition?.itemName)
    }

    @Test
    fun ignoresMissingPreEvolution() {
        // Pichu n'existe pas en 1re génération : Pikachu est la racine.
        val trees = EvolutionTree.build(
            members = mapOf(25 to "Pikachu", 26 to "Raichu"),
            edges = listOf(
                EvolutionEdge(172, 25, EvolutionCondition("level-up")),
                EvolutionEdge(25, 26, EvolutionCondition("use-item", itemName = "Pierre Foudre"))
            )
        )
        assertEquals(listOf(25), trees.map { it.pokemonId })
        assertEquals(listOf(26), trees.single().children.map { it.pokemonId })
    }
}
