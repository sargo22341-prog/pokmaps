package org.opensources.pokmaps.domain.pokedex

import org.opensources.pokmaps.domain.model.PokedexEntry

/** Noms immuables normalisés une fois ; captures et favoris restent ceux des entrées courantes. */
class PokedexSearchIndex(entries: List<PokedexEntry>) {
    private val names = entries.associate {
        it.pokemonId to (PokedexSearch.normalize(it.name) to PokedexSearch.normalize(it.nameEn))
    }

    fun filter(entries: List<PokedexEntry>, filter: PokedexFilter, limit: Int = Int.MAX_VALUE): List<PokedexEntry> =
        PokedexSearch.filter(entries, filter, names, limit)
}
