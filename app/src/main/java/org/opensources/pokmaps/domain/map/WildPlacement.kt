package org.opensources.pokmaps.domain.map

import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.random.Random

/** Position d'un marqueur, en pixels de la carte affichée. */
data class Placed<T>(val item: T, val x: Int, val y: Int)

/**
 * Répartition des Pokémon sauvages d'un terrain (herbes, eau, sol) sur ses emplacements : chaque Pokémon est
 * dessiné plusieurs fois (les plus fréquents davantage), à des emplacements tirés au hasard, pour montrer qu'on
 * le rencontre partout sur le terrain. Le tirage est déterministe : un lieu s'affiche toujours de la même façon.
 */
object WildPlacement {
    /** Nombre maximal de marqueurs d'un même Pokémon sur un terrain. */
    const val MAX_COPIES = 4

    /** Écart (en pixels) entre les marqueurs qui doivent partager un emplacement (plus de Pokémon que de places). */
    private const val CLUSTER_RADIUS = 14.0
    private const val GOLDEN_ANGLE = 2.399963

    /**
     * Nombre de marqueurs de chaque Pokémon : un au moins chacun, puis les emplacements libres partagés selon
     * les poids (probabilités de rencontre), sans dépasser [MAX_COPIES].
     */
    fun copies(weights: List<Double>, spots: Int): List<Int> {
        if (weights.isEmpty()) return emptyList()
        val total = max(weights.size, min(spots, weights.size * MAX_COPIES))
        val shares = if (weights.all { it > 0.0 }) weights else weights.map { 1.0 }
        val sum = shares.sum()
        val copies = MutableList(weights.size) { 1 }
        repeat(total - weights.size) {
            // La copie suivante va au Pokémon le plus en retard sur sa part.
            val next = weights.indices.filter { copies[it] < MAX_COPIES }
                .maxByOrNull { shares[it] / sum * total - copies[it] } ?: return copies
            copies[next]++
        }
        return copies
    }

    /**
     * Place les éléments (dans l'ordre de leurs poids décroissants de préférence) sur les emplacements,
     * ou autour de `fallback` sans emplacement.
     */
    fun <T> place(
        items: List<T>,
        weights: List<Double>,
        spots: List<Pair<Int, Int>>,
        fallback: Pair<Int, Int>,
        seed: Int
    ): List<Placed<T>> {
        val cells = spots.shuffled(Random(seed)).ifEmpty { listOf(fallback) }
        val copies = copies(weights, cells.size)
        // Ordre alterné (A, B, C, A, B, A…) : les marqueurs d'un même Pokémon sont dispersés sur le terrain.
        val order = (0 until (copies.maxOrNull() ?: 0)).flatMap { round ->
            items.indices.filter { copies[it] > round }
        }
        return order.mapIndexed { index, item ->
            val (x, y) = cells[index % cells.size]
            val ring = index / cells.size
            if (ring == 0) {
                Placed(items[item], x, y)
            } else {
                // Plus de marqueurs que d'emplacements : les suivants entourent l'emplacement.
                val angle = index * GOLDEN_ANGLE
                Placed(
                    items[item],
                    x + (cos(angle) * CLUSTER_RADIUS * ring).roundToInt(),
                    y + (sin(angle) * CLUSTER_RADIUS * ring).roundToInt()
                )
            }
        }
    }
}
