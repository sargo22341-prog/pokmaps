package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.map.GameIndex
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.PokedexEntry

/** Les noms issus de la base enrichissent aussi les conditions de succès, hors du rendu Compose. */
internal class GuideMentions(pokemon: List<PokedexEntry>, catalog: MapCatalog, index: GameIndex) {
    private val targets: Map<String, GuideTarget> = buildMap {
        catalog.maps.values.sortedByDescending { it.identifier.length }.forEach {
            put(normalize(it.name), GuideTarget.Place(it.identifier))
        }
        catalog.objects.values.flatten().filter { it.kind == MapObjectKind.NPC || it.kind == MapObjectKind.TRAINER }
            .groupBy { it.name }.filter { (name, _) -> name in CHARACTER_NAMES }
            .forEach { (name, objects) ->
                val character = objects.maxBy { obj -> index.offers.count { it.objectId == obj.id } }
                put(normalize(name), GuideTarget.Character(character.id))
            }
        CHARACTER_ALIASES.forEach { (label, location) ->
            val map = catalog.mapByIdentifier(location.first)
            val character = map?.let {
                catalog.objects[it.id].orEmpty().firstOrNull { obj ->
                    obj.name == location.second || obj.name == label
                }
            }
            if (character != null) put(normalize(label), GuideTarget.Character(character.id))
        }
        index.items.forEach { put(normalize(it.name), GuideTarget.Item(it.identifier)) }
        pokemon.forEach { put(normalize(it.name), GuideTarget.Pokemon(it.pokemonId)) }
    }.filterKeys { it.length >= 3 }
    private val pattern = Regex(
        "(?<![\\p{L}\\p{N}])(?:" + targets.keys.sortedByDescending {
            it.length
        }.joinToString("|") { Regex.escape(it) } +
            ")(?![\\p{L}\\p{N}])"
    )

    fun link(paragraphs: List<List<GuideSpan>>): List<List<GuideSpan>> = paragraphs.map { paragraph ->
        paragraph.flatMap { span -> if (span.target == null) linkText(span.text) else listOf(span) }
    }

    private fun linkText(text: String): List<GuideSpan> {
        val result = mutableListOf<GuideSpan>()
        var start = 0
        for (match in pattern.findAll(normalize(text))) {
            if (start < match.range.first) result += GuideSpan(text.substring(start, match.range.first))
            result += GuideSpan(text.substring(match.range), targets.getValue(match.value))
            start = match.range.last + 1
        }
        if (start < text.length) result += GuideSpan(text.substring(start))
        return result.toList()
    }

    private fun normalize(text: String): String = text.replace('’', '\'')

    private companion object {
        val CHARACTER_NAMES = setOf(
            "Pierre", "Ondine", "Major Bob", "Érika", "Koga", "Morgane", "Auguste", "Giovanni",
            "Albert", "Hector", "Blanche", "Mortimer", "Chuck", "Jasmine", "Frédo", "Sandra", "Jeannine",
            "Fargas", "Buena", "Red", "Eusine", "Léo", "Peter"
        )
        val CHARACTER_ALIASES = mapOf(
            "Professeur Chen" to ("oaks-lab" to "Prof. Chen"),
            "Professeur Orme" to ("elms-lab" to "Prof. Orme"),
            "Peter" to ("lances-room" to "Maître"),
            "M. Fuji" to ("mr-fujis-house" to "Fuji"),
            "Blue" to ("viridian-gym" to "Blue")
        )
    }
}
