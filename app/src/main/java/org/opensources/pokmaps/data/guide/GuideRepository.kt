package org.opensources.pokmaps.data.guide

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.domain.guide.CaptureGoals
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.guide.parseGuideText
import org.opensources.pokmaps.domain.map.GameIndex
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.model.Game

class GuideRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val maps: MapRepository,
    private val pokedex: PokedexRepository
) {
    suspend fun library(game: Game): GuideLibrary = withContext(Dispatchers.IO) {
        val catalog = maps.catalog(game)
        val entries = pokedex.pokedex(game)
        val pokemonIds = entries.map { it.pokemonId }.toSet()
        val index = maps.index(game)
        val mentions = GuideMentions(entries, catalog, index)
        val definitions = kantoGuides() + johtoGuides() + sideGuides() + tipGuides() + achievementGuides()
        val selected = definitions.filter { game.versionId in it.versions }
        val articles = selected.map { definition ->
            require(definition.pokemonId in pokemonIds) { "Sprite absent : ${definition.id}" }
            GuideArticle(
                definition.id,
                context.getString(definition.title),
                definition.category,
                mentions.link(
                    parseGuideText(context.getString(definition.text)) { kind, value ->
                        resolve(kind, value, catalog, pokemonIds, index)
                    }
                ),
                definition.pokemonId,
                definition.sources,
                definition.relatedIds + selected.filter { it.chapter == definition.id }.map { it.id },
                definition.missable,
                definition.captureIds,
                definition.achievementId,
                definition.points,
                definition.achievementId?.let(CaptureGoals::forAchievement)
            )
        }
        GuideLibrary(game, articles)
    }

    private fun resolve(
        kind: String,
        value: String,
        catalog: MapCatalog,
        pokemonIds: Set<Int>,
        index: GameIndex
    ): GuideTarget = when (kind) {
        "pokemon" -> GuideTarget.Pokemon(value.toInt().also { require(it in pokemonIds) { "Pokémon absent : $value" } })

        "place" -> GuideTarget.Place(
            value.also {
                require(catalog.mapByIdentifier(it) != null) { "Lieu absent : $value" }
            }
        )

        "item" -> GuideTarget.Item(
            value.also {
                require(index.items.any { it.identifier == value }) { "Objet absent : $value" }
            }
        )

        "character" -> {
            val (place, name) = value.split(":", limit = 2)
            val map = requireNotNull(catalog.mapByIdentifier(place)) { "Lieu absent : $place" }
            val locator = name.split("~")
            val character = requireNotNull(
                catalog.objects[map.id]?.singleOrNull { obj ->
                    if (name.startsWith("@")) {
                        index.offers.any {
                            it.objectId == obj.id && it.itemIdentifier == name.drop(1)
                        }
                    } else {
                        obj.name == locator[0] && (
                            locator.size == 1 ||
                                (locator.size == 3 && obj.x == locator[1].toInt() && obj.y == locator[2].toInt())
                            )
                    }
                }
            ) {
                "Personnage absent : $value"
            }
            GuideTarget.Character(character.id)
        }

        else -> error("Type de lien inconnu : $kind")
    }
}
