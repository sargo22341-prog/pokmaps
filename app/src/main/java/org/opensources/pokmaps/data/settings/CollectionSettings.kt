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
        preferences.asMap().filterKeys { it.name.startsWith(CAUGHT_PREFIX) }.map { (key, value) ->
            val versionId = requireNotNull(key.name.removePrefix(CAUGHT_PREFIX).toIntOrNull()) {
                "Version de collection invalide : ${key.name}"
            }
            require(versionId > 0 && key.name == "$CAUGHT_PREFIX$versionId") {
                "Version de collection invalide : ${key.name}"
            }
            val ids = requireNotNull(value as? Set<*>) { "Collection invalide : ${key.name}" }
            require(ids.all { it is String }) { "Collection invalide : ${key.name}" }
            versionId to ids.map { it.toString() }.toSet().toIds()
        }.toMap()
    }.distinctUntilChanged()

    /** Identifiants du catalogue de formes, mémorisés indépendamment de la capture de l’espèce. */
    val formsByVersion: Flow<Map<Int, Set<String>>> = dataStore.data.map { preferences ->
        preferences.asMap().filterKeys { it.name.startsWith(FORM_PREFIX) }.map { (key, value) ->
            val version = requireNotNull(key.name.removePrefix(FORM_PREFIX).toIntOrNull())
            require(version > 0 && key.name == "$FORM_PREFIX$version")
            require(value is Set<*> && value.all { it is String && it.matches(FORM_IDENTIFIER) })
            version to value.map { it.toString() }.toSet()
        }.toMap()
    }.distinctUntilChanged()

    suspend fun setFormCaught(versions: Set<Int>, identifier: String, caught: Boolean) {
        require(versions.all { it > 0 } && identifier.matches(FORM_IDENTIFIER))
        dataStore.edit { preferences ->
            versions.forEach { version ->
                val key = stringSetPreferencesKey("$FORM_PREFIX$version")
                val recorded = preferences[key].orEmpty()
                val updated = if (caught) recorded + identifier else recorded - identifier
                if (updated.isEmpty()) preferences.remove(key) else preferences[key] = updated
            }
        }
    }

    /** Portée des captures ; un identifiant inconnu revient à la portée par défaut. */
    val captureScope: Flow<CaptureScope> = dataStore.data.map { preferences ->
        preferences[CAPTURE_SCOPE]?.let { CaptureScope.fromIdentifier(it) } ?: CaptureScope.DEFAULT
    }.distinctUntilChanged()

    suspend fun setFavorite(pokemonId: Int, favorite: Boolean) {
        require(pokemonId > 0) { "Identifiant Pokémon invalide : $pokemonId" }
        dataStore.edit { it[FAVORITES] = it[FAVORITES].orEmpty().with(pokemonId, favorite) }
    }

    /** Coche (ou décoche) le Pokémon dans chacune de ces versions, en une seule écriture. */
    suspend fun setCaught(versionIds: Set<Int>, pokemonId: Int, caught: Boolean) {
        require(pokemonId > 0 && versionIds.all { it > 0 }) { "Identifiants de collection invalides" }
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

    private fun Set<String>?.toIds(): Set<Int> = orEmpty().map { value ->
        val id = requireNotNull(value.toIntOrNull()) { "Identifiant Pokémon invalide : $value" }
        require(id > 0 && value == id.toString()) { "Identifiant Pokémon invalide : $value" }
        id
    }.toSet()

    private fun Set<String>.with(pokemonId: Int, present: Boolean): Set<String> =
        if (present) this + pokemonId.toString() else this - pokemonId.toString()

    private companion object {
        val FAVORITES = stringSetPreferencesKey("favorite_pokemon")
        val CAPTURE_SCOPE = stringPreferencesKey("capture_scope")
        val FORM_IDENTIFIER = Regex("[a-z0-9-]{1,100}")
        const val FORM_PREFIX = "caught_form_"
        const val CAUGHT_PREFIX = "caught_pokemon_"
    }
}
