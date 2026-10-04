package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.obtainMethods

@Singleton
class PokedexRepository @Inject constructor(private val dao: PokedexDao) {
    /** Pokédex du jeu : types de la génération et façons d'obtenir chaque Pokémon dans la version. */
    suspend fun pokedex(game: Game): List<PokedexEntry> {
        val types = dao.pokemonTypes(game.generationId).groupBy({ it.pokemonId }) {
            PokemonType(it.id, it.identifier, it.name)
        }
        val encounters = (dao.encounterMethods(game.versionId) + dao.staticPokemon(game.versionGroupId))
            .groupBy({ it.pokemonId }) { ObtainMethod.fromEncounterMethod(it.method) }
            .mapValues { (_, methods) -> methods.filterNotNull().toSet() }
        val methods = obtainMethods(encounters, dao.evolutions(game.versionGroupId).map { it.fromId to it.toId })
        return dao.pokedex(game.versionGroupId).map { row ->
            PokedexEntry(
                number = row.number,
                pokemonId = row.pokemonId,
                name = row.name,
                nameEn = row.nameEn,
                types = types[row.pokemonId].orEmpty(),
                obtainMethods = methods[row.pokemonId].orEmpty()
            )
        }
    }

    suspend fun types(game: Game): List<PokemonType> =
        dao.types(game.generationId).map { PokemonType(it.id, it.identifier, it.name) }
}
