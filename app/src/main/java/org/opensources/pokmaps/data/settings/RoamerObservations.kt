package org.opensources.pokmaps.data.settings

import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringSetPreferencesKey
import org.opensources.pokmaps.domain.guide.SinnohRoamerObservations

internal fun readRoamerObservations(preferences: Preferences, version: Int): Map<Int, String> {
    val values = preferences[stringSetPreferencesKey("sinnoh_roamers_$version")].orEmpty()
    require(values.size <= 5)
    val pairs = values.map {
        val parts = it.split(":", limit = 2)
        require(parts.size == 2)
        val pokemon = parts[0].toInt()
        require(parts[0] == pokemon.toString())
        pokemon to parts[1]
    }
    require(pairs.map { it.first }.distinct().size == pairs.size)
    return pairs.toMap().also { SinnohRoamerObservations.validate(version, it) }
}
