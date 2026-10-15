package org.opensources.pokmaps.di

import android.content.Context
import android.content.pm.PackageManager
import android.content.res.AssetManager
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.MoveDao
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.data.db.PokedexDatabase
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.data.map.AssetFiles
import org.opensources.pokmaps.data.map.AssetManagerFiles

@Module
@InstallIn(SingletonComponent::class)
object DataModule {
    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): PokedexDatabase {
        val installedAt = context.packageManager
            .getPackageInfo(context.packageName, PackageManager.PackageInfoFlags.of(0))
            .lastUpdateTime
        val name = "pokedex-$installedAt.db"
        return Room
            .databaseBuilder(context, PokedexDatabase::class.java, name)
            .createFromAsset(PokedexDatabase.ASSET)
            .fallbackToDestructiveMigration(dropAllTables = true)
            .addCallback(object : RoomDatabase.Callback() {
                override fun onOpen(db: SupportSQLiteDatabase) {
                    removePreviousDatabases(context, name)
                }
            })
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
    fun moveDao(database: PokedexDatabase): MoveDao = database.moveDao()

    @Provides
    fun assets(@ApplicationContext context: Context): AssetManager = context.assets

    @Provides
    fun assetFiles(files: AssetManagerFiles): AssetFiles = files

    /** Calculs (conversions, index) à garder hors du fil principal ; les tests injectent leur propre répartiteur. */
    @Provides
    fun computationDispatcher(): CoroutineDispatcher = Dispatchers.Default
}

/**
 * Chaque installation ouvre une nouvelle copie. Le nettoyage des copies précédentes attend l'ouverture réussie,
 * sur l'exécuteur Room ; aucune lecture de préférences ou suppression n'a lieu dans le provider Hilt.
 */
internal fun removePreviousDatabases(context: Context, currentName: String) {
    context.databaseList().filter { it == PokedexDatabase.NAME || it.matches(INSTALL_DATABASE) }.forEach { name ->
        if (name != currentName) {
            check(context.deleteDatabase(name)) { "Impossible de retirer l'ancienne base : $name" }
        }
    }
}

private val INSTALL_DATABASE = Regex("pokedex-[0-9]+\\.db")
