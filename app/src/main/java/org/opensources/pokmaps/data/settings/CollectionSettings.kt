package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.MutablePreferences
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.pokedex.CaptureScope

/**
 * Collection de l'utilisateur, mémorisée avec DataStore : Pokémon capturés dans chaque version (la progression
 * de Rouge et celle de Bleu sont distinctes), portée des captures (réglage) et Pokémon favoris, communs à tous
 * les jeux.
 */
@Singleton
class CollectionSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    val favorites: Flow<Set<Int>> = dataStore.data.map { it[FAVORITES].toIds() }.distinctUntilChanged()

    /** Pokémon capturés, par version (identifiant PokéAPI) : une clé de préférences par version. */
    val caughtByVersion: Flow<Map<Int, Set<Int>>> = dataStore.data.map { preferences ->
        preferences.asMap().mapNotNull { (key, value) ->
            val versionId = key.name.takeIf { it.startsWith(CAUGHT_PREFIX) }?.removePrefix(CAUGHT_PREFIX)?.toIntOrNull()
            val ids = (value as? Set<*>)?.filterIsInstance<String>()?.toSet()
            if (versionId == null || ids == null) null else versionId to ids.toIds()
        }.toMap()
    }.distinctUntilChanged()

    /** Portée des captures ; un identifiant inconnu (réglage d'une autre version) revient à la portée par défaut. */
    val captureScope: Flow<CaptureScope> = dataStore.data.map { preferences ->
        preferences[CAPTURE_SCOPE]?.let { CaptureScope.fromIdentifier(it) } ?: CaptureScope.DEFAULT
    }.distinctUntilChanged()

    suspend fun setFavorite(pokemonId: Int, favorite: Boolean) {
        dataStore.edit { it[FAVORITES] = it[FAVORITES].orEmpty().with(pokemonId, favorite) }
    }

    /** Coche (ou décoche) le Pokémon dans chacune de ces versions, en une seule écriture. */
    suspend fun setCaught(versionIds: Set<Int>, pokemonId: Int, caught: Boolean) {
        dataStore.edit { preferences -> versionIds.forEach { preferences.setCaught(it, pokemonId, caught) } }
    }

    suspend fun setCaptureScope(scope: CaptureScope) {
        dataStore.edit { it[CAPTURE_SCOPE] = scope.identifier }
    }

    private fun MutablePreferences.setCaught(versionId: Int, pokemonId: Int, caught: Boolean) {
        val key = stringSetPreferencesKey("$CAUGHT_PREFIX$versionId")
        val ids = this[key].orEmpty().with(pokemonId, caught)
        if (ids.isEmpty()) remove(key) else this[key] = ids
    }

    private fun Set<String>?.toIds(): Set<Int> = orEmpty().mapNotNull { it.toIntOrNull() }.toSet()

    private fun Set<String>.with(pokemonId: Int, present: Boolean): Set<String> =
        if (present) this + pokemonId.toString() else this - pokemonId.toString()

    private companion object {
        val FAVORITES = stringSetPreferencesKey("favorite_pokemon")
        val CAPTURE_SCOPE = stringPreferencesKey("capture_scope")
        const val CAUGHT_PREFIX = "caught_pokemon_"
    }
}
