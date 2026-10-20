package org.opensources.pokmaps.domain.sinnoh

data class UndergroundPrice(val sphere: Int, val minimum: Int, val maximumExclusive: Int) {
    init {
        require(sphere in 0..6 && minimum in 0..99 && maximumExclusive in minimum..99)
        require(sphere == 0 || maximumExclusive > minimum)
    }
}

data class UndergroundGood(
    val id: Int,
    val name: String,
    val width: Int,
    val depth: Int,
    val price: UndergroundPrice,
    val money: Int,
    val national: Boolean,
    val available: Boolean
) {
    init {
        require(id in 7..138 && name.isNotBlank() && width in 0..3 && depth in 0..3 && money >= 0)
    }
}

data class UndergroundTrap(val id: Int, val name: String, val price: UndergroundPrice) {
    init {
        require(id in 1..33 && name.isNotBlank() && price.sphere != 0)
    }
}

data class MiningTreasure(val id: Int, val name: String, val weights: List<Int>) {
    init {
        require(id in 1..59 && name.isNotBlank())
        require(weights.size == 4 && weights.all { it in 0..1000 })
    }
}

data class SinnohUnderground(
    val goods: List<UndergroundGood>,
    val traps: List<UndergroundTrap>,
    val mining: List<MiningTreasure>
)
