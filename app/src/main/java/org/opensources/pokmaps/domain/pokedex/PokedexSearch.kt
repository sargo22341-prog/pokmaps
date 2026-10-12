package org.opensources.pokmaps.domain.pokedex

import java.text.Normalizer
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry

/** Pokémon capturés ou non dans la version choisie. */
enum class CaughtFilter {
    ALL,
    CAUGHT,
    MISSING
}

/** Critères de la liste du Pokédex : texte recherché, type, disponibilité, méthode d'obtention, capture et favoris. */
data class PokedexFilter(
    val query: String = "",
    val typeId: Int? = null,
    val availableOnly: Boolean = false,
    val method: ObtainMethod? = null,
    val caught: CaughtFilter = CaughtFilter.ALL,
    val favoritesOnly: Boolean = false
) {
    val isActive: Boolean
        get() = typeId != null || availableOnly || method != null || caught != CaughtFilter.ALL || favoritesOnly
}

/**
 * Recherche dans le Pokédex, insensible à la casse et aux accents (« evoli » trouve « Évoli »),
 * par nom français ou anglais, ou par numéro (« 25 », « 025 », « n°25 », « #25 »).
 */
object PokedexSearch {
    fun filter(entries: List<PokedexEntry>, filter: PokedexFilter): List<PokedexEntry> =
        filter(entries, filter, null, Int.MAX_VALUE)

    internal fun filter(
        entries: List<PokedexEntry>,
        filter: PokedexFilter,
        names: Map<Int, Pair<String, String>>?,
        limit: Int
    ): List<PokedexEntry> {
        require(limit >= 0) { "Limite de recherche négative" }
        val query = normalize(filter.query)
        val number = query.removePrefix("n°").removePrefix("no").removePrefix("#").trim().toIntOrNull()
        return entries.asSequence().filter { entry ->
            (filter.typeId == null || entry.types.any { it.id == filter.typeId }) &&
                (!filter.availableOnly || entry.isAvailable) &&
                (filter.method == null || filter.method in entry.obtainMethods) &&
                (!filter.favoritesOnly || entry.favorite) &&
                when (filter.caught) {
                    CaughtFilter.ALL -> true
                    CaughtFilter.CAUGHT -> entry.caught
                    CaughtFilter.MISSING -> !entry.caught
                } &&
                (query.isEmpty() || entry.matches(query, number, names))
        }.take(limit).toList()
    }

    private fun PokedexEntry.matches(query: String, number: Int?, names: Map<Int, Pair<String, String>>?): Boolean {
        if (number != null) return this.number == number
        val normalized = if (names == null) {
            normalize(name) to normalize(nameEn)
        } else {
            checkNotNull(names[pokemonId]) { "Pokémon absent de l’index : $pokemonId" }
        }
        return normalized.first.contains(query) || normalized.second.contains(query)
    }

    /** Minuscules sans accents ni espaces superflus ; ♀ et ♂ deviennent « f » et « m » (« nidoran f »). */
    fun normalize(text: String): String = Normalizer.normalize(text.trim().lowercase(), Normalizer.Form.NFD)
        .replace(DIACRITICS, "")
        .replace("♀", " f")
        .replace("♂", " m")
        .replace(SPACES, " ")
        .trim()

    private val DIACRITICS = Regex("\\p{Mn}+")
    private val SPACES = Regex("\\s+")
}

/**
 * Façons d'obtenir chaque Pokémon dans une version : ses rencontres (capture, don, échange…)
 * et l'évolution, pour tout Pokémon dont une pré-évolution est disponible.
 *
 * @param encounters méthodes de rencontre directes de chaque Pokémon
 * @param evolutions évolutions du jeu (de, vers)
 */
fun obtainMethods(
    encounters: Map<Int, Set<ObtainMethod>>,
    evolutions: List<Pair<Int, Int>>
): Map<Int, Set<ObtainMethod>> {
    val result = encounters.mapValues { it.value.toMutableSet() }.toMutableMap()
    var changed = true
    while (changed) {
        changed = false
        for ((from, to) in evolutions) {
            if (result[from].isNullOrEmpty()) continue
            if (result.getOrPut(to) { mutableSetOf() }.add(ObtainMethod.EVOLUTION)) changed = true
        }
    }
    return result
}
