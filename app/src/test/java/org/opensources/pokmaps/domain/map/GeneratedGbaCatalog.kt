package org.opensources.pokmaps.domain.map

import java.io.File
import java.util.Properties
import org.sqlite.JDBC

/** Instantané de la phase cartes GBA, sans introduire les jeux incomplets dans Room. */
internal object GeneratedGbaCatalog {
    fun load(group: String): MapCatalog {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        val assets = requireNotNull(database.parentFile?.parentFile) { "Chemin des assets absent : $database" }
        val folder = assets.resolve("maps/$group")
        val events = readEvents(database, group)
        val rows = readRows(folder.resolve("catalog.tsv"))
        val ids = rows.associate { it.getValue("const") to it.getValue("number").toInt() }
        val maps = rows.map { row ->
            MapInfo(
                row.getValue("number").toInt(), identifier(row.getValue("const")), row.getValue("name_fr"),
                ids[row.getValue("parent")], row.getValue("x").toInt(), row.getValue("y").toInt(),
                row.getValue("width").toInt(), row.getValue("height").toInt(), row.getValue("level_count").toInt(),
                row.getValue("is_world") == "True", ids[row.getValue("origin")], ids[row.getValue("start")],
                events[identifier(row.getValue("const"))]?.first,
                events[identifier(row.getValue("const"))]?.second ?: 0
            )
        }.associateBy { it.id }
        val warps = readRows(folder.resolve("warps.tsv")).mapIndexed { index, row ->
            MapWarp(
                index,
                ids.getValue(row.getValue("map_const")),
                row.getValue("x").toInt(),
                row.getValue("y").toInt(),
                ids[row.getValue("target")],
                row.getValue("target_x").toIntOrNull(),
                row.getValue("target_y").toIntOrNull()
            )
        }.groupBy { it.mapId }
        return MapCatalog(group, maps, warps, emptyMap(), emptyMap())
    }

    private fun readEvents(database: File, group: String): Map<String, Pair<String?, Int>> =
        checkNotNull(JDBC().connect("jdbc:sqlite:${database.path}", Properties())).use { connection ->
            connection.prepareStatement(
                "SELECT m.identifier, m.external_event_key, m.event_entrance FROM map m " +
                    "JOIN version_group vg ON vg.id = m.version_group_id WHERE vg.identifier = ?"
            ).use { query ->
                query.setString(1, group)
                query.executeQuery().use { rows ->
                    buildMap {
                        while (rows.next()) {
                            put(rows.getString(1), rows.getString(2) to rows.getInt(3))
                        }
                    }
                }
            }
        }

    private fun readRows(file: File): List<Map<String, String>> {
        require(file.isFile) { "Asset GBA absent : $file" }
        val lines = file.readLines()
        require(lines.size in 2..4096) { "Catalogue GBA vide ou trop grand : $file" }
        val fields = lines.first().split('\t')
        return lines.drop(1).map { line ->
            val values = line.split('\t')
            require(values.size == fields.size) { "Ligne GBA invalide : $file" }
            fields.zip(values).toMap()
        }
    }

    private fun identifier(const: String): String = const.removePrefix("MAP_").lowercase().replace('_', '-')
}
