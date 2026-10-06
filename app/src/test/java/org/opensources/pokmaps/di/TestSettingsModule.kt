package org.opensources.pokmaps.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import dagger.Module
import dagger.Provides
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import dagger.hilt.testing.TestInstallIn
import java.io.File
import javax.inject.Singleton

/**
 * Préférences neuves pour chaque test UI : le DataStore de l'application est un singleton du processus, il
 * garderait sinon le jeu choisi ou la collection d'un test à l'autre.
 */
@Module
@TestInstallIn(components = [SingletonComponent::class], replaces = [SettingsModule::class])
object TestSettingsModule {
    @Provides
    @Singleton
    fun settings(@ApplicationContext context: Context): DataStore<Preferences> {
        val file = File.createTempFile("settings", ".preferences_pb", context.cacheDir)
        // DataStore crée le fichier lui-même : un fichier vide existant serait lu comme corrompu.
        check(file.delete()) { "Fichier temporaire impossible à supprimer : $file" }
        return PreferenceDataStoreFactory.create { file }
    }
}
