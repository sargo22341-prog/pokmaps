package org.opensources.pokmaps.di

import android.content.Context
import android.content.pm.PackageManager
import android.content.res.AssetManager
import androidx.core.content.edit
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.db.PokemonDao

internal val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

@Module
@InstallIn(SingletonComponent::class)
object DataModule {
    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): PokedexDatabase {
        refreshDatabaseAfterUpdate(context)
        return Room
            .databaseBuilder(context, PokedexDatabase::class.java, PokedexDatabase.NAME)
            .createFromAsset(PokedexDatabase.ASSET)
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
    }

    @Provides
    fun gameDao(database: PokedexDatabase): GameDao = database.gameDao()

    @Provides
    fun pokedexDao(database: PokedexDatabase): PokedexDao = database.pokedexDao()

    @Provides
    fun mapDao(database: PokedexDatabase): MapDao = database.mapDao()

    @Provides
    fun pokemonDao(database: PokedexDatabase): PokemonDao = database.pokemonDao()

    @Provides
    @Singleton
    fun settings(@ApplicationContext context: Context): DataStore<Preferences> = context.settingsDataStore

    @Provides
    fun assets(@ApplicationContext context: Context): AssetManager = context.assets
}

/**
 * La base n'est copiée depuis les assets qu'au premier lancement : après une mise à jour de l'application
 * (nouvelles données à version de schéma égale), on supprime la copie pour que Room la recopie.
 * Les données de l'utilisateur ne sont jamais stockées dans cette base.
 */
internal fun refreshDatabaseAfterUpdate(context: Context) {
    val installedAt = context.packageManager
        .getPackageInfo(context.packageName, PackageManager.PackageInfoFlags.of(0))
        .lastUpdateTime
    val preferences = context.getSharedPreferences("database", Context.MODE_PRIVATE)
    if (preferences.getLong(KEY_COPIED_FOR, 0L) != installedAt) {
        context.deleteDatabase(PokedexDatabase.NAME)
        preferences.edit { putLong(KEY_COPIED_FOR, installedAt) }
    }
}

private const val KEY_COPIED_FOR = "copied_for_install"
