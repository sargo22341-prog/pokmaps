package org.opensources.pokmaps.domain.hoenn

enum class ContestCategory { COOL, BEAUTY, CUTE, SMART, TOUGH }

data class Berry(
    val identifier: String,
    val name: String,
    val stageHours: Int,
    val minYield: Int,
    val maxYield: Int,
    val smoothness: Int,
    val flavors: List<Int>
) {
    init {
        require(stageHours in 1..24 && minYield in 1..maxYield && maxYield <= 15)
        require(smoothness in 0..255 && flavors.size == 5 && flavors.all { it in 0..40 })
        require(identifier.isNotBlank() && name.isNotBlank())
    }
}

data class ContestMove(
    val category: ContestCategory,
    val appeal: Int,
    val jam: Int,
    val effect: String,
    val previous: List<String>
) {
    init {
        require(appeal in 0..8 && jam in 0..8 && effect.isNotBlank())
        require(previous.size <= 4 && previous.all { it.isNotBlank() })
    }
}

data class Decoration(val identifier: String, val name: String, val shape: String, val price: Int) {
    init {
        require(identifier.startsWith("DECOR_") && name.isNotBlank() && price >= 0)
        require(shape.matches(Regex("[1-4]x[1-4]")))
    }
}

data class DecorationSource(
    val identifier: String,
    val version: String,
    val map: String,
    val gift: Boolean,
    val price: Int?,
    val currency: org.opensources.pokmaps.domain.map.OfferCurrency
) {
    init {
        require(identifier.startsWith("DECOR_") && version in setOf("ruby", "sapphire", "emerald"))
        require(map.matches(Regex("[a-z0-9]+(-[a-z0-9]+)*")))
        require(price == null || price >= 0)
        require(currency == org.opensources.pokmaps.domain.map.OfferCurrency.MONEY || price != null)
    }
}

data class HoennContent(
    val berries: Map<String, Berry>,
    val moves: Map<Int, ContestMove>,
    val decorations: List<Decoration>,
    val sources: List<DecorationSource>
)
