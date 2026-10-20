package org.opensources.pokmaps.domain.sinnoh

data class BattleConfiguration(
    val id: Int,
    val species: Int,
    val name: String,
    val moves: List<Int>,
    val moveNames: List<String>,
    val item: String,
    val nature: String,
    val evs: Int,
    val form: Int
) {
    init {
        require(id in 1..950 && species in 1..493 && name.isNotBlank() && nature.isNotBlank())
        require(moves.size == 4 && moves.all { it in 0..467 })
        require(moveNames.size == moves.count { it != 0 } && moveNames.all { it.isNotBlank() })
        require(evs in 0..63 && form in 0..5)
    }
}

data class BattleSeries(val number: Int, val ordinary: IntRange, val last: IntRange) {
    init {
        require(number in 1..8)
        require(ordinary.first in 0..299 && ordinary.last in ordinary.first..299)
        require(last.first in 0..299 && last.last in last.first..299)
    }
}

data class FactoryPool(val trainerLimit: Int, val first: Int, val last: Int, val ivs: Int, val upgrade: Boolean) {
    init {
        require(first in 1..950 && last in first..950 && ivs in 0..31)
        require(trainerLimit in 1..311)
    }
}

data class SinnohFrontier(
    val castle: List<BattleSeries>,
    val arcade: List<BattleSeries>,
    val factory: List<BattleSeries>,
    val level50: List<FactoryPool>,
    val openPlayer: List<FactoryPool>,
    val openOpponent: List<FactoryPool>,
    val hall: List<BattleConfiguration>,
    val hallRanks: List<IntRange>
)

data class SinnohBattles(
    val configurations: Map<Int, BattleConfiguration>,
    val trainers: List<List<Int>>,
    val tower: List<BattleSeries>,
    val frontier: SinnohFrontier?
) {
    fun possibilities(range: IntRange): List<BattleConfiguration> = range.flatMap { trainers[it] }
        .distinct().sorted().map(configurations::getValue)
}
