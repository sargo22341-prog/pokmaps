package org.opensources.pokmaps.domain.map

import java.io.File

/** Instantané de la phase cartes GBA, sans introduire les jeux incomplets dans Room. */
internal object GeneratedHoennCatalog {
    fun load(group: String): MapCatalog {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        val assets = requireNotNull(database.parentFile?.parentFile) { "Chemin des assets absent : $database" }
        val folder = assets.resolve("maps/$group")
        val rows = readRows(folder.resolve("catalog.tsv"))
        val ids = rows.associate { it.getValue("const") to it.getValue("number").toInt() }
        val maps = rows.map { row ->
            MapInfo(
                row.getValue("number").toInt(), identifier(row.getValue("const")), row.getValue("name_fr"),
                ids[row.getValue("parent")], row.getValue("x").toInt(), row.getValue("y").toInt(),
                row.getValue("width").toInt(), row.getValue("height").toInt(), row.getValue("level_count").toInt(),
                row.getValue("is_world") == "True", ids[row.getValue("origin")], ids[row.getValue("start")]
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

    private fun readRows(file: File): List<Map<String, String>> {
        require(file.isFile) { "Asset Hoenn absent : $file" }
        val lines = file.readLines()
        require(lines.size in 2..4096) { "Catalogue Hoenn vide ou trop grand : $file" }
        val fields = lines.first().split('\t')
        return lines.drop(1).map { line ->
            val values = line.split('\t')
            require(values.size == fields.size) { "Ligne Hoenn invalide : $file" }
            fields.zip(values).toMap()
        }
    }

    private fun identifier(const: String): String = const.removePrefix("MAP_").lowercase().replace('_', '-')
}
