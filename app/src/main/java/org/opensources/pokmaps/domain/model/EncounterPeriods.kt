package org.opensources.pokmaps.domain.model

/** Les périodes sans différence n'ajoutent aucun choix à la liste du lieu. */
data class EncounterPeriods(val sections: List<TimedEncounters>, val selected: Set<EncounterTime>) {
    private val varyingTimes = sections.flatMap { it.groups }.flatMap { it.encounters }
        .filter { it.times.size < EncounterTime.entries.size }.flatMap { it.times }.toSet()
    val available: List<TimeFilter> = TimeFilter.entries.filter { it.time in varyingTimes }
    val allSelected: Boolean = available.all { it.time in selected }
    private val filtered: List<TimedEncounters> = sections.mapNotNull { section ->
        if (section.period != TimeFilter.ALL && section.period.time !in selected) return@mapNotNull null
        val groups = section.groups.mapNotNull { group ->
            val encounters = group.encounters.filter {
                it.times.size == EncounterTime.entries.size || it.matchesTimes(selected)
            }
            group.copy(encounters = encounters).takeIf { encounters.isNotEmpty() }
        }
        section.copy(groups = groups).takeIf { groups.isNotEmpty() }
    }
    val shown: List<TimedEncounters> = EncounterSection.entries.flatMap { kind ->
        filtered.mapNotNull { section ->
            val encounters = section.groups.flatMap { it.encounters }.filter { EncounterSection.of(it) == kind }
            section.copy(groups = encounters.groupByMethod()).takeIf { encounters.isNotEmpty() }
        }
    }
    private val visibleSpecies = shown.flatMap { it.groups }.groupBy { it.methodName }.mapValues { (_, groups) ->
        groups.flatMap { it.encounters }.map { Triple(it.versionId, it.areaId, it.pokemonId) }.toSet()
    }
    val groups: List<EncounterGroup> = sections.flatMap { it.groups }.flatMap { group ->
        val visible = visibleSpecies[group.methodName].orEmpty()
        group.encounters.filter { Triple(it.versionId, it.areaId, it.pokemonId) in visible }
    }.distinct().groupByMethod()
    val drySections: List<TimedEncounters> = shown.filter { section -> section.groups.none { it.water } }
    val waterSections: List<TimedEncounters> = shown.filter { section -> section.groups.any { it.water } }
    val waterHabitat: EncounterHabitat = waterSections.firstOrNull()?.groups?.firstOrNull()
        ?.encounters?.firstOrNull()?.habitat ?: EncounterHabitat.GRASS
    private val encounters = shown.flatMap { it.groups }.flatMap { it.encounters }
    val availableMethods: List<EncounterFilter> = EncounterFilter.entries.filter { method ->
        encounters.any { method.matches(it) }
    }

    fun toggle(period: TimeFilter): Set<EncounterTime> {
        val time = period.time ?: return EncounterTime.entries.toSet()
        return if (time in selected) selected - time else selected + time
    }
}

private enum class EncounterSection {
    LAND,
    OTHER,
    WATER;

    companion object {
        fun of(encounter: Encounter): EncounterSection = when {
            encounter.isWater -> WATER
            encounter.isWild -> LAND
            else -> OTHER
        }
    }
}
