package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Place occupée par le dessin d'un marqueur à sa taille normale (échelle 1), en pixels de la carte, sans les marges
 * transparentes de l'image.
 */
data class Footprint(val width: Double, val height: Double) {
    val area: Double get() = width * height

    companion object {
        /** Pokémon (icône de boîte : le dessin occupe environ 62 % × 78 % de ses 68 × 56 pixels). */
        val POKEMON = Footprint(42.0, 44.0)

        /** Objet (icône pokesprite de 32 pixels, dessin d'environ 24 pixels). */
        val ITEM = Footprint(24.0, 24.0)

        /** Personnage : une case du jeu. */
        val CHARACTER = Footprint(16.0, 16.0)
    }
}

/**
 * Taille des marqueurs selon la place disponible, commune à tous les jeux : sur un terrain donné, les marqueurs
 * ne couvrent pas plus de [MAX_COVERAGE] de sa surface et ne se chevauchent pas. Un grand terrain avec peu de
 * Pokémon les garde à leur taille normale ; un petit terrain (étang, couloir de grotte) ou un terrain très peuplé
 * les réduit, tous de la même façon pour rester cohérent, jusqu'à [MIN_SCALE] au plus petit.
 */
object MarkerSizing {
    /** Taille minimale d'un marqueur (environ une case pour un Pokémon). */
    const val MIN_SCALE = 0.4f

    /** Part maximale d'un terrain couverte par les marqueurs : la carte reste lisible sous eux. */
    const val MAX_COVERAGE = 0.15

    /**
     * Surface (en pixels²) que représente un emplacement : les emplacements des terrains sont espacés de trois
     * cases (16 pixels) au moins, chacun couvre donc environ 3 × 3 cases du terrain.
     */
    const val SPOT_AREA = 9 * 16.0 * 16.0

    /** Surface d'un terrain, estimée d'après le nombre de ses emplacements. */
    fun terrainArea(spots: Int): Double = spots * SPOT_AREA

    /** Nombre de marqueurs que le terrain peut recevoir à leur taille normale. */
    fun capacity(area: Double, footprint: Footprint): Int = floor(MAX_COVERAGE * area / footprint.area).toInt()

    /** Taille commune de `count` marqueurs pour qu'ils ne couvrent pas plus de [MAX_COVERAGE] du terrain. */
    fun coverageScale(area: Double, count: Int, footprint: Footprint): Float {
        if (count <= 0) return 1f
        return clamp(sqrt(MAX_COVERAGE * area / (count * footprint.area)))
    }

    /** Plus grande taille commune des marqueurs placés en `positions` sans que deux d'entre eux se chevauchent. */
    fun spacingScale(positions: List<Pair<Int, Int>>, footprint: Footprint): Float {
        val separations = separations(positions, positions, footprint)
        return clamp(separations.minOrNull() ?: Double.MAX_VALUE)
    }

    /**
     * Taille commune de marqueurs qu'on ne peut pas déplacer (objets, personnages, Pokémon fixes), d'après la
     * place autour de chacun (`neighbors` : tous les marqueurs voisins, eux compris). Quelques marqueurs collés
     * l'un à l'autre ne réduisent pas tous les autres : on retient la place du premier quart des plus serrés.
     */
    fun crowdScale(positions: List<Pair<Int, Int>>, neighbors: List<Pair<Int, Int>>, footprint: Footprint): Float {
        val separations = separations(positions, neighbors, footprint).sorted()
        if (separations.isEmpty()) return 1f
        return clamp(separations[separations.size / CROWD_QUANTILE])
    }

    /**
     * Pour chaque marqueur, plus grande taille à laquelle il ne chevauche aucun voisin : deux rectangles centrés
     * sur leurs positions se touchent quand leur écart dépasse à la fois la largeur et la hauteur du dessin.
     */
    private fun separations(
        positions: List<Pair<Int, Int>>,
        neighbors: List<Pair<Int, Int>>,
        footprint: Footprint
    ): List<Double> = positions.mapNotNull { (x, y) ->
        var skipped = false
        neighbors.mapNotNull { other ->
            // Le marqueur lui-même (une seule fois : deux marqueurs au même endroit se chevauchent).
            if (!skipped && other.first == x && other.second == y) {
                skipped = true
                null
            } else {
                max(abs(other.first - x) / footprint.width, abs(other.second - y) / footprint.height)
            }
        }.minOrNull()
    }

    /**
     * Taille de chaque objet, personnage et Pokémon fixe (par identifiant) : commune à ceux d'un même lieu qui
     * se dessinent pareil, d'après la place laissée par tous les autres marqueurs du lieu.
     */
    fun objectScales(objects: List<MapObject>): Map<Int, Float> = buildMap {
        objects.groupBy { it.mapId }.values.forEach { inPlace ->
            val neighbors = inPlace.map { it.x to it.y }
            inPlace.groupBy { footprintOf(it) }.forEach { (footprint, group) ->
                val scale = crowdScale(group.map { it.x to it.y }, neighbors, footprint)
                group.forEach { put(it.id, scale) }
            }
        }
    }

    /** Place occupée par le dessin d'un objet de la carte : icône d'objet, de Pokémon, ou sprite d'une case. */
    fun footprintOf(obj: MapObject): Footprint = when {
        obj.itemIdentifier != null -> Footprint.ITEM
        obj.kind == MapObjectKind.POKEMON && obj.pokemonId != null -> Footprint.POKEMON
        else -> Footprint.CHARACTER
    }

    private fun clamp(scale: Double): Float = min(1.0, max(MIN_SCALE.toDouble(), scale)).toFloat()

    /** Le premier quart des marqueurs les plus serrés décide de la taille. */
    private const val CROWD_QUANTILE = 4
}
