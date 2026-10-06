package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt
import kotlin.random.Random

/**
 * Position d'un marqueur, en pixels de la carte affichée, et sa taille (1 = taille normale, plus petit quand
 * le terrain manque de place pour tous les Pokémon, voir [MarkerSizing]).
 */
data class Placed<T>(val item: T, val x: Int, val y: Int, val scale: Float = 1f)

/**
 * Répartition des Pokémon sauvages d'un terrain (herbes, eau, sol) sur ses emplacements : chaque Pokémon est
 * dessiné une fois au moins, les plus fréquents parfois davantage s'il y a de la place, à des emplacements bien
 * répartis, sans surcharger la carte. Le nombre et la taille des marqueurs s'adaptent à la surface du terrain
 * ([MarkerSizing]) : beaucoup de place et peu de Pokémon, ils sont grands et parfois en double ; peu de place ou
 * beaucoup de Pokémon, ils sont uniques et plus petits. Le tirage est déterministe : un lieu s'affiche toujours de
 * la même façon. Rien ici ne dépend d'un jeu en particulier.
 */
object WildPlacement {
    /** Nombre maximal de marqueurs d'un même Pokémon sur un terrain. */
    const val MAX_COPIES = 2

    /** Nombre maximal de marqueurs d'un terrain (sauf s'il y a davantage de Pokémon différents). */
    const val MAX_MARKERS = 8

    /** Taille des Pokémon rangés en grille faute de terrain connu (aucun emplacement). */
    private const val GRID_SCALE = 0.6f

    /** Marge (en pixels) entre deux Pokémon rangés en grille. */
    private const val GRID_GAP = 2.0

    /**
     * Écart minimal (en pixels, deux cases) entre un Pokémon et un objet, un personnage ou une entrée, sur l'un
     * des deux axes : l'icône d'un Pokémon est large d'environ deux cases.
     */
    private const val CLEAR_X = 32.0
    private const val CLEAR_Y = 32.0

    /**
     * Nombre de marqueurs de chaque Pokémon : un au moins chacun, puis des copies pour les plus fréquents tant
     * que le terrain a de la place (`room` marqueurs à leur taille normale), sans dépasser [MAX_COPIES] chacun ni
     * [MAX_MARKERS] en tout.
     */
    fun copies(weights: List<Double>, room: Int): List<Int> {
        if (weights.isEmpty()) return emptyList()
        val wanted = minOf(room, weights.size * MAX_COPIES, MAX_MARKERS)
        val total = max(weights.size, wanted)
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
     * Emplacements assez loin des objets, personnages et entrées (`obstacles`) pour qu'on ne touche pas un
     * Pokémon à la place de l'un d'eux. S'il en reste moins que `minimum` (un par Pokémon), les emplacements
     * les moins encombrés complètent.
     */
    fun awayFrom(spots: List<Pair<Int, Int>>, obstacles: List<Pair<Int, Int>>, minimum: Int): List<Pair<Int, Int>> {
        if (obstacles.isEmpty()) return spots
        // Distance au plus proche obstacle, en multiples de l'écart voulu (1 = juste assez loin).
        fun clearance(spot: Pair<Int, Int>): Double = obstacles.minOf { (x, y) ->
            max(abs(spot.first - x) / CLEAR_X, abs(spot.second - y) / CLEAR_Y)
        }
        val (clear, crowded) = spots.partition { clearance(it) >= 1.0 }
        if (clear.size >= minimum) return clear
        return clear + crowded.sortedByDescending(::clearance).take(minimum - clear.size)
    }

    /**
     * Place les éléments (dans l'ordre de leurs poids décroissants de préférence) sur les emplacements du terrain,
     * à une taille adaptée à sa surface `area` (estimée d'après ses emplacements par défaut) et à la place
     * occupée par chaque marqueur (`footprint`). Sans assez d'emplacements pour tous, ils sont rangés en grille au
     * milieu du terrain (ou autour de `fallback`).
     */
    fun <T> place(
        items: List<T>,
        weights: List<Double>,
        spots: List<Pair<Int, Int>>,
        fallback: Pair<Int, Int>,
        seed: Int,
        footprint: Footprint = Footprint.POKEMON,
        area: Double = MarkerSizing.terrainArea(spots.size)
    ): List<Placed<T>> {
        if (items.isEmpty()) return emptyList()
        if (spots.size < items.size) {
            val scale = if (spots.isEmpty()) GRID_SCALE else MarkerSizing.coverageScale(area, items.size, footprint)
            return grid(items, middle(spots) ?: fallback, footprint, scale)
        }
        val room = min(spots.size, MarkerSizing.capacity(area, footprint))
        val copies = copies(weights, room)
        val cells = spread(spots.shuffled(Random(seed)), copies.sum())
        val scale = min(
            MarkerSizing.coverageScale(area, cells.size, footprint),
            MarkerSizing.spacingScale(cells, footprint)
        )
        // Ordre alterné (A, B, C, A, B…) : les marqueurs d'un même Pokémon sont dispersés sur le terrain.
        val order = (0 until (copies.maxOrNull() ?: 0)).flatMap { round ->
            items.indices.filter { copies[it] > round }
        }
        return order.mapIndexed { index, item ->
            Placed(items[item], cells[index].first, cells[index].second, scale)
        }
    }

    /**
     * `count` emplacements aussi éloignés que possible les uns des autres : chaque nouvel emplacement est celui
     * qui est le plus loin de ceux déjà choisis (le premier est tiré au hasard).
     */
    private fun spread(cells: List<Pair<Int, Int>>, count: Int): List<Pair<Int, Int>> {
        val chosen = mutableListOf(cells.first())
        val remaining = cells.drop(1).toMutableList()
        while (chosen.size < count && remaining.isNotEmpty()) {
            val next = remaining.maxBy { cell -> chosen.minOf { distance2(it, cell) } }
            remaining.remove(next)
            chosen += next
        }
        return chosen
    }

    /** Emplacement le plus proche du centre du terrain. */
    private fun middle(spots: List<Pair<Int, Int>>): Pair<Int, Int>? {
        if (spots.isEmpty()) return null
        val center = spots.sumOf { it.first } / spots.size to spots.sumOf { it.second } / spots.size
        return spots.minBy { distance2(it, center) }
    }

    /**
     * Un marqueur réduit par élément, en grille presque carrée centrée sur `center` (la dernière ligne centrée),
     * côte à côte sans se chevaucher.
     */
    private fun <T> grid(items: List<T>, center: Pair<Int, Int>, footprint: Footprint, scale: Float): List<Placed<T>> {
        val columns = ceil(sqrt(items.size.toDouble())).toInt()
        val rows = ceil(items.size / columns.toDouble()).toInt()
        val stepX = footprint.width * scale + GRID_GAP
        val stepY = footprint.height * scale + GRID_GAP
        return items.mapIndexed { index, item ->
            val row = index / columns
            val inRow = min(columns, items.size - row * columns)
            val column = index % columns
            Placed(
                item,
                center.first + ((column - (inRow - 1) / 2.0) * stepX).roundToInt(),
                center.second + ((row - (rows - 1) / 2.0) * stepY).roundToInt(),
                scale
            )
        }
    }

    private fun distance2(a: Pair<Int, Int>, b: Pair<Int, Int>): Int {
        val dx = a.first - b.first
        val dy = a.second - b.second
        return dx * dx + dy * dy
    }
}
