package org.opensources.pokmaps.domain.guide

data class CaptureChoice(val alternatives: List<Set<Int>>) {
    init {
        require(alternatives.isNotEmpty() && alternatives.all { it.isNotEmpty() })
        require(alternatives.map { it.size }.distinct().size == 1)
        require(alternatives.sumOf { it.size } == alternatives.flatten().distinct().size)
    }

    val total: Int = alternatives.first().size
    fun count(caught: Set<Int>): Int = alternatives.maxOf { option -> option.count { it in caught } }
}

data class CaptureGoal(val fixed: Set<Int>, val choices: List<CaptureChoice>) {
    val species: Set<Int> = fixed + choices.flatMap { it.alternatives.flatten() }
    val total: Int = fixed.size + choices.sumOf { it.total }

    init {
        require(species.all { it in 1..251 })
        require(species.size == fixed.size + choices.sumOf { it.alternatives.sumOf { option -> option.size } })
    }

    fun count(caught: Set<Int>): Int = fixed.count { it in caught } + choices.sumOf { it.count(caught) }
}

/** Choix mutuellement exclusifs sur une cartouche sans échange externe ni duplication de pierres. */
object CaptureGoals {
    fun forAchievement(id: Int): CaptureGoal? = when (id) {
        4425 -> kanto(RED_MISSING, yellow = false)
        540348 -> kanto(BLUE_MISSING, yellow = false)
        4450 -> kanto(YELLOW_MISSING, yellow = true)
        5090 -> johto(GOLD_MISSING, fire = listOf(59, 136))
        5120 -> johto(SILVER_MISSING, fire = listOf(38, 136))
        5954 -> goal((1..251).toSet() - CRYSTAL_MISSING, listOf(JOHTO_STARTERS))
        else -> null
    }

    private fun kanto(missing: Set<Int>, yellow: Boolean): CaptureGoal {
        val choices = listOf(
            CaptureChoice(listOf(setOf(138, 139), setOf(140, 141))),
            singles(listOf(106, 107)),
            singles(listOf(134, 135, 136))
        ) + if (yellow) emptyList() else listOf(KANTO_STARTERS)
        return goal((1..151).toSet() - missing, choices)
    }

    private fun johto(missing: Set<Int>, fire: List<Int>): CaptureGoal = goal(
        (1..251).toSet() - missing,
        listOf(
            JOHTO_STARTERS,
            singles(listOf(62, 91, 121, 134)),
            singles(fire),
            singles(listOf(45, 71, 103)),
            singles(listOf(26, 135))
        )
    )

    private fun goal(available: Set<Int>, choices: List<CaptureChoice>): CaptureGoal {
        val alternatives = choices.flatMap { it.alternatives.flatten() }.toSet()
        require(available.containsAll(alternatives))
        return CaptureGoal(available - alternatives, choices)
    }

    private fun singles(ids: List<Int>) = CaptureChoice(ids.map { setOf(it) })

    private val KANTO_STARTERS = CaptureChoice(listOf(setOf(1, 2, 3), setOf(4, 5, 6), setOf(7, 8, 9)))
    private val JOHTO_STARTERS = CaptureChoice(listOf(setOf(152, 153, 154), setOf(155, 156, 157), setOf(158, 159, 160)))
    private val TRADE_EVOLUTIONS = setOf(65, 68, 76, 94)
    private val RED_MISSING = TRADE_EVOLUTIONS + setOf(27, 28, 37, 38, 52, 53, 69, 70, 71, 126, 127, 151)
    private val BLUE_MISSING = TRADE_EVOLUTIONS + setOf(23, 24, 43, 44, 45, 56, 57, 58, 59, 123, 125, 151)
    private val YELLOW_MISSING = setOf(13, 14, 15, 23, 24, 26, 52, 53, 65, 76, 94, 109, 110, 124, 125, 126, 151)
    private val JOHTO_COMMON_MISSING = (1..9).toSet() + setOf(
        65, 68, 76, 94, 138, 139, 140, 141, 144, 145, 146, 150, 151, 186, 199, 208, 212, 230, 233, 251
    )
    private val GOLD_MISSING = JOHTO_COMMON_MISSING + setOf(37, 38, 52, 53, 165, 166, 225, 227, 231, 232)
    private val SILVER_MISSING = JOHTO_COMMON_MISSING + setOf(56, 57, 58, 59, 167, 168, 207, 216, 217, 226)
    private val CRYSTAL_MISSING = JOHTO_COMMON_MISSING + setOf(37, 38, 56, 57, 179, 180, 181, 203, 223, 224)
}
