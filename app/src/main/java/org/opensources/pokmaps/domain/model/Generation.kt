package org.opensources.pokmaps.domain.model

/** Générations prises en charge ; chaque mécanique décide explicitement de ses règles. */
enum class Generation(val id: Int, val maximumSpecies: Int) {
    GEN1(1, 151),
    GEN2(2, 251),
    GEN3(3, 386),
    GEN4(4, 493);

    companion object {
        val maximumSupportedSpecies: Int = entries.maxOf { it.maximumSpecies }

        fun of(id: Int): Generation = requireNotNull(entries.firstOrNull { it.id == id }) {
            "Génération sans règles dans l'application : $id"
        }
    }
}
