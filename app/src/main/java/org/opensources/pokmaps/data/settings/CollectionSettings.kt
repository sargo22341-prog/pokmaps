package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map

/**
 * Collection de l'utilisateur, mémorisée avec DataStore : Pokémon capturés dans chaque version (la progression
 * de Rouge et celle de Bleu sont distinctes) et Pokémon favoris, communs à tous les jeux.
 */
@Singleton
class CollectionSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    val favorites: Flow<Set<Int>> = dataStore.data.map { it[FAVORITES].toIds() }.distinctUntilChanged()

    fun caught(versionId: Int): Flow<Set<Int>> =
        dataStore.data.map { it[caughtKey(versionId)].toIds() }.distinctUntilChanged()

    suspend fun setFavorite(pokemonId: Int, favorite: Boolean) {
        dataStore.edit { it[FAVORITES] = it[FAVORITES].orEmpty().with(pokemonId, favorite) }
    }

    suspend fun setCaught(versionId: Int, pokemonId: Int, caught: Boolean) {
        val key = caughtKey(versionId)
        dataStore.edit { it[key] = it[key].orEmpty().with(pokemonId, caught) }
    }

    private fun Set<String>?.toIds(): Set<Int> = orEmpty().mapNotNull { it.toIntOrNull() }.toSet()

    private fun Set<String>.with(pokemonId: Int, present: Boolean): Set<String> =
        if (present) this + pokemonId.toString() else this - pokemonId.toString()

    private companion object {
        val FAVORITES = stringSetPreferencesKey("favorite_pokemon")

        fun caughtKey(versionId: Int) = stringSetPreferencesKey("caught_pokemon_$versionId")
    }
}
