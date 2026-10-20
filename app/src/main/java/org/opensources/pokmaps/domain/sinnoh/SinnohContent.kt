package org.opensources.pokmaps.domain.sinnoh

import org.opensources.pokmaps.domain.hoenn.ContestCategory

data class SinnohBerry(
    val identifier: String,
    val name: String,
    val stageHours: Int,
    val maxYield: Int,
    val drainRate: Int,
    val smoothness: Int,
    val flavors: List<Int>
) {
    init {
        require(identifier.endsWith("-berry") && name.isNotBlank())
        require(stageHours in 1..24 && maxYield in 5..15 && drainRate in 1..100)
        require(smoothness in 0..255 && flavors.size == 5 && flavors.all { it in 0..40 })
    }

    fun stageMinutes(mulch: Mulch): Int = when (mulch) {
        Mulch.NONE, Mulch.STABLE, Mulch.GOOEY -> stageHours * 60
        Mulch.GROWTH -> stageHours * 60 * 3 / 4
        Mulch.DAMP -> stageHours * 90
    }

    fun hourlyDrain(mulch: Mulch): Int = when (mulch) {
        Mulch.NONE, Mulch.STABLE, Mulch.GOOEY -> drainRate
        Mulch.GROWTH -> drainRate + drainRate / 2
        Mulch.DAMP -> drainRate / 2
    }
}

enum class Mulch { NONE, GROWTH, DAMP, STABLE, GOOEY }

data class SuperContestMove(val category: ContestCategory, val appeal: Int, val effect: String) {
    init {
        require(appeal in 0..4 && effect.isNotBlank())
    }
}

data class SinnohContent(
    val berries: Map<String, SinnohBerry>,
    val moves: Map<Int, SuperContestMove>,
    val underground: SinnohUnderground,
    val battles: SinnohBattles
)
