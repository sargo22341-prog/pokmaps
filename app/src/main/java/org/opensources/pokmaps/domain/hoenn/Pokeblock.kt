package org.opensources.pokmaps.domain.hoenn

sealed interface Pokeblock {
    val feel: Int

    data class Recipe(val flavors: List<Int>, override val feel: Int) : Pokeblock {
        init {
            require(flavors.size == 5 && flavors.all { it in 0..255 } && flavors.any { it > 0 })
            require(feel in 0..255)
        }

        val level: Int get() = flavors.max()
    }

    /** Le moteur tire trois faibles saveurs : une recette ne prédit pas ce tirage. */
    data class Black(override val feel: Int) : Pokeblock {
        init {
            require(feel in 0..255)
        }
    }
}

/** maxRpmHundredths reprend l'entier du moteur (100 = un tour par minute). */
fun blendPokeblock(berries: List<Berry>, maxRpmHundredths: Int = 0): Pokeblock {
    require(berries.size in 2..4 && maxRpmHundredths in 0..65535)
    val totals = List(5) { flavor -> berries.sumOf { it.flavors[flavor] } }
    val differences = List(5) { flavor -> totals[flavor] - totals[(flavor + 1) % 5] }
    val negatives = differences.count { it < 0 }
    val base = differences.map { (it.coerceAtLeast(0) - negatives).coerceAtLeast(0) }
    val feel = (berries.sumOf { it.smoothness } / berries.size - berries.size).coerceIn(0, 255)
    if (berries.map { it.identifier }.distinct().size != berries.size || negatives > 3 || base.all { it == 0 }) {
        return Pokeblock.Black(feel)
    }
    val multiplier = maxRpmHundredths / 333 + 100
    val flavors = base.map { value ->
        val scaled = value * multiplier / 10
        (scaled / 10 + if (scaled % 10 > 4) 1 else 0).coerceAtMost(255)
    }
    return Pokeblock.Recipe(flavors, feel)
}
