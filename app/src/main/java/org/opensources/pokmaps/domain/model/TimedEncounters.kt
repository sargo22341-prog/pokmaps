package org.opensources.pokmaps.domain.model

data class TimedSpecies(val pokemonId: Int, val name: String, val encounters: List<Encounter>) {
    val waterMethods: Map<WaterMethod, List<Encounter>> = WaterMethod.entries.associateWith { method ->
        encounters.filter { method.matches(it.method) }
    }
}

data class TimedMethod(
    val name: String,
    val species: List<TimedSpecies>,
    val aquatic: Boolean = false,
    val habitat: EncounterHabitat = EncounterHabitat.GRASS,
    val landscape: Boolean = true
)

data class TimedEncounters(val period: TimeFilter, val groups: List<EncounterGroup>) {
    val methods: List<TimedMethod> = groups.map { group ->
        TimedMethod(group.methodName, group.species, group.aquatic, group.habitat, group.landscape)
    }
}

/** Fusionne seulement les rencontres dont niveaux, probabilités et autres conditions sont identiques. */
fun List<Encounter>.byTime(filter: TimeFilter): List<TimedEncounters> {
    val merged = groupBy {
        it.copy(
            times = emptySet(),
            conditions = it.nonTimeConditions,
            conditionKeys = it.conditionKeys.filterNot { key -> key.startsWith("time-") }.toSet(),
            conditionNames = it.conditionNames.filterKeys { key -> !key.startsWith("time-") }
        )
    }
        .map { (encounter, variants) ->
            val times = if (variants.any { it.times.isEmpty() }) emptySet() else variants.flatMap { it.times }.toSet()
            encounter.copy(times = times)
        }
    if (filter != TimeFilter.ALL) {
        return listOf(TimedEncounters(filter, merged.filter { it.matchesTimes(filter.times) }.groupByMethod()))
    }
    val always = merged.groupBy {
        it.copy(times = emptySet(), minLevel = 0, maxLevel = 0, chance = null)
    }.values.filter { variants ->
        variants.any { it.times.isEmpty() } || variants.flatMap { it.times }.toSet().size == EncounterTime.entries.size
    }.flatten()
    val sections = listOf(TimedEncounters(TimeFilter.ALL, always.groupByMethod())) +
        listOf(TimeFilter.MORNING, TimeFilter.DAY, TimeFilter.NIGHT).map { period ->
            TimedEncounters(period, merged.filter { it !in always && it.matchesTimes(period.times) }.groupByMethod())
        }
    return sections.filter { it.groups.isNotEmpty() }
}
