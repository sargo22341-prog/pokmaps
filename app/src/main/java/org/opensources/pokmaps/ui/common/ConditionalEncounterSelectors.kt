package org.opensources.pokmaps.ui.common

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import org.opensources.pokmaps.domain.model.Encounter

@Composable
internal fun ConditionalEncounterSelectors(
    encounters: List<Encounter>,
    safari: String?,
    contestDay: String?,
    onSafari: (String) -> Unit,
    onContestDay: (String) -> Unit
) {
    val options = remember(encounters) {
        encounters.flatMap { it.conditionNames.entries }.associate { it.key to it.value }
    }
    ConditionalEncounterSelector(options, "hgss-safari-", safari, "-base", onSafari)
    ConditionalEncounterSelector(options, "hgss-contest-", contestDay, "-1", onContestDay)
}

@Composable
private fun ConditionalEncounterSelector(
    options: Map<String, String>,
    prefix: String,
    selected: String?,
    defaultSuffix: String,
    onSelect: (String) -> Unit
) {
    val keys = options.keys.filter { it.startsWith(prefix) }.sorted()
    if (keys.isEmpty()) return
    val active = selected?.takeIf { it in keys } ?: keys.firstOrNull { it.endsWith(defaultSuffix) } ?: keys.first()
    CompactSelect(active, keys, onSelect) { requireNotNull(options[it]) }
}
