package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow

/** Préférences en mémoire ; `failing` simule un fichier de préférences illisible. */
internal class FakeDataStore(private val failing: Boolean = false) : DataStore<Preferences> {
    private val state = MutableStateFlow(emptyPreferences())

    override val data: Flow<Preferences> = if (failing) flow { throw IOException("Préférences illisibles") } else state

    override suspend fun updateData(transform: suspend (t: Preferences) -> Preferences): Preferences {
        if (failing) throw IOException("Préférences illisibles")
        return transform(state.value).also { state.value = it }
    }
}
