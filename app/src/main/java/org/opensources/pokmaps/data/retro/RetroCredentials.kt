package org.opensources.pokmaps.data.retro

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

internal class RetroAccount(val username: String, val apiKey: String) {
    init {
        require(username.matches(Regex("[A-Za-z0-9_-]{1,32}")))
        require(apiKey.matches(Regex("[A-Za-z0-9]{32}")))
    }

    override fun toString(): String = "RetroAccount"
}

/** La clé reste chiffrée dans noBackupFilesDir ; elle ne quitte pas l'appareil lors d'une sauvegarde. */
@Singleton
class RetroCredentials @Inject constructor(@ApplicationContext context: Context) {
    private val file = AtomicFile(File(context.noBackupFilesDir, "retroachievements.credentials"))

    internal suspend fun read(): RetroAccount? = withContext(Dispatchers.IO) {
        if (!file.baseFile.exists()) return@withContext null
        val bytes = file.openRead().use { it.readNBytes(MAX_BYTES + 1) }
        require(bytes.size in 29..MAX_BYTES)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, IV_SIZE)))
        val json = JSONObject(String(cipher.doFinal(bytes.copyOfRange(IV_SIZE, bytes.size)), Charsets.UTF_8))
        RetroAccount(json.getString("username"), json.getString("key"))
    }

    internal suspend fun save(account: RetroAccount) = withContext(Dispatchers.IO) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val json = JSONObject().put("username", account.username).put("key", account.apiKey).toString()
        val bytes = cipher.iv + cipher.doFinal(json.toByteArray(Charsets.UTF_8))
        val output = file.startWrite()
        try {
            output.write(bytes)
            file.finishWrite(output)
        } catch (error: Exception) {
            file.failWrite(output)
            throw error
        }
    }

    suspend fun delete() = withContext(Dispatchers.IO) { file.delete() }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = store.getKey(ALIAS, null)
        if (existing != null) return existing as SecretKey
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build()
        )
        return generator.generateKey()
    }

    private companion object {
        const val MAX_BYTES = 4096
        const val IV_SIZE = 12
        const val ALIAS = "pokmaps.retroachievements"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
