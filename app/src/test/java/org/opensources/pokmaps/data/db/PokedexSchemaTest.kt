package org.opensources.pokmaps.data.db

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.io.File
import java.sql.Connection
import java.sql.DriverManager
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/**
 * Vérifie que la base générée par tools/build_data.py correspond exactement aux entités Room
 * (tables, colonnes, types, NOT NULL, clés primaires, index), comme Room le contrôle à l'ouverture
 * de la base pré-remplie. Ignoré si la base n'a pas été générée.
 */
class PokedexSchemaTest {
    private lateinit var connection: Connection
    private lateinit var schema: JsonObject

    @Before
    fun setUp() {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        val schemaFile = File(
            System.getProperty("pokemaps.roomSchemas").orEmpty(),
            "${PokedexDatabase::class.java.name}/${PokedexDatabase.VERSION}.json"
        )
        assumeTrue("Base absente : lancer tools/build_data.py", database.isFile)
        assertEquals("Schéma Room introuvable : $schemaFile", true, schemaFile.isFile)
        schema = JsonParser.parseString(schemaFile.readText()).asJsonObject.getAsJsonObject("database")
        connection = DriverManager.getConnection("jdbc:sqlite:${database.path}")
    }

    @After
    fun tearDown() {
        if (::connection.isInitialized) connection.close()
    }

    @Test
    fun versionMatches() {
        assertEquals(PokedexDatabase.VERSION, schema.get("version").asInt)
        assertEquals(PokedexDatabase.VERSION, query("PRAGMA user_version").single().single().toInt())
    }

    @Test
    fun tablesMatch() {
        val tables = query(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).map { it.single() }
        assertEquals(entities().map { it.get("tableName").asString }.sorted(), tables)
    }

    @Test
    fun columnsMatch() {
        for (entity in entities()) {
            val table = entity.get("tableName").asString
            val primaryKey = entity.getAsJsonObject("primaryKey").getAsJsonArray("columnNames").map { it.asString }
            val expected = entity.getAsJsonArray("fields").map { it.asJsonObject }.map { field ->
                val name = field.get("columnName").asString
                Column(
                    name,
                    field.get("affinity").asString,
                    field.get("notNull").asBoolean,
                    primaryKey.indexOf(name) + 1
                )
            }.sortedBy { it.name }
            // PRAGMA table_info : cid, name, type, notnull, dflt_value, pk
            val actual = query("PRAGMA table_info(`$table`)").map {
                Column(it[1], it[2], it[3] == "1", it[5].toInt())
            }.sortedBy { it.name }
            assertEquals("Colonnes de $table", expected, actual)
        }
    }

    @Test
    fun indicesMatch() {
        for (entity in entities()) {
            val table = entity.get("tableName").asString
            val expected = entity.getAsJsonArray("indices")?.map { it.asJsonObject }.orEmpty().associate { index ->
                index.get("name").asString to index.getAsJsonArray("columnNames").map { it.asString }
            }
            // PRAGMA index_list : seq, name, unique, origin, partial (origin c = CREATE INDEX)
            val actual = query("PRAGMA index_list(`$table`)").filter { it[3] == "c" }.associate { row ->
                row[1] to query("PRAGMA index_info(`${row[1]}`)").sortedBy { it[0].toInt() }.map { it[2] }
            }
            assertEquals("Index de $table", expected, actual)
        }
    }

    private data class Column(val name: String, val type: String, val notNull: Boolean, val primaryKeyPosition: Int)

    private fun entities(): List<JsonObject> = schema.getAsJsonArray("entities").map { it.asJsonObject }

    private fun query(sql: String): List<List<String>> = connection.createStatement().use { statement ->
        statement.executeQuery(sql).use { result ->
            val columns = result.metaData.columnCount
            buildList {
                while (result.next()) add((1..columns).map { result.getString(it).orEmpty() })
            }
        }
    }
}
