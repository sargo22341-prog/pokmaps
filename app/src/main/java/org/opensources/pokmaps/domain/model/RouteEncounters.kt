package org.opensources.pokmaps.domain.model

enum class GbaCartridge(val condition: String) {
    NONE("slot2-none"),
    RUBY("slot2-ruby"),
    SAPPHIRE("slot2-sapphire"),
    EMERALD("slot2-emerald"),
    FIRERED("slot2-firered"),
    LEAFGREEN("slot2-leafgreen")
}

/** Conditions choisies pour une route ; les errants ont leur liste séparée. */
data class RouteEncounterFilter(
    val cartridge: GbaCartridge = GbaCartridge.NONE,
    val roaming: Boolean = false,
    val radar: Boolean = false,
    val swarm: Boolean = false,
    val nationalDex: Boolean = false,
    val daily: Boolean = false,
    val gifts: Boolean = false
) {
    init {
        require(!roaming || !gifts)
    }

    fun matches(encounter: Encounter): Boolean {
        if (encounter.method.startsWith("roaming-") != roaming) return false
        if ((ObtainMethod.fromEncounterMethod(encounter.method) == ObtainMethod.GIFT) != gifts) return false
        if (gifts) return true
        val keys = encounter.conditionKeys
        if (keys.any { it.startsWith("slot2-") } && cartridge.condition !in keys) return false
        if (("radar-on" in keys && !radar) || ("radar-off" in keys && radar)) return false
        if (("swarm-yes" in keys && !swarm) || ("swarm-no" in keys && swarm)) return false
        if (!roaming && "story-progress-national-dex" in keys && !nationalDex) return false
        if (!roaming && "story-progress-before-national-dex" in keys && nationalDex) return false
        if (("backlot-mentioned" in keys && !daily) || ("backlot-not-mentioned" in keys && daily)) return false
        return true
    }

    /** Additionne les emplacements actifs identiques sans répéter les conditions déjà choisies. */
    fun apply(encounters: List<Encounter>): List<Encounter> {
        val active = encounters.filter(::matches).map(::withoutSelectedConditions)
        return active.groupBy { if (it.chance == null) it else it.copy(chance = 0.0) }.map { (_, rows) ->
            val first = rows.first()
            if (first.chance == null) first else first.copy(chance = rows.sumOf { requireNotNull(it.chance) })
        }
    }

    private fun withoutSelectedConditions(encounter: Encounter): Encounter {
        if (gifts || encounter.conditionNames.isEmpty()) return encounter
        val remaining = encounter.conditionNames.filterKeys { !isSelectedCondition(it) }
        return encounter.copy(
            conditionNames = remaining,
            conditionKeys = encounter.conditionKeys.filterNot(::isSelectedCondition).toSet(),
            conditions = remaining.values.joinToString(", ").ifEmpty { null },
            nonTimeConditions = remaining.filterKeys { !it.startsWith("time-") }
                .values.joinToString(", ").ifEmpty { null }
        )
    }

    private fun isSelectedCondition(key: String): Boolean = key.startsWith("slot2-") ||
        key in setOf(
            "radar-on",
            "radar-off",
            "swarm-yes",
            "swarm-no",
            "backlot-mentioned",
            "backlot-not-mentioned",
            "story-progress-national-dex",
            "story-progress-before-national-dex"
        )
}
