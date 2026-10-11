package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.PokedexCatalog
import org.opensources.pokmaps.domain.pokedex.obtainMethods

@Singleton
class PokedexRepository @Inject constructor(private val dao: PokedexDao) {
    suspend fun catalogs(game: Game): List<PokedexCatalog> =
        dao.catalogs(game.versionGroupId).map { PokedexCatalog(it.id, it.name) }

    /** Pokédex choisi, régional par défaut, avec les façons d’obtenir chaque Pokémon dans la version. */
    suspend fun pokedex(game: Game, pokedexId: Int? = null): List<PokedexEntry> {
        val catalogs = catalogs(game)
        val selected = if (pokedexId == null) catalogs.firstOrNull() else catalogs.firstOrNull { it.id == pokedexId }
        checkNotNull(selected) { "Pokédex absent du jeu ${game.versionIdentifier} : $pokedexId" }
        val types = dao.pokemonTypes(game.generationId).groupBy({ it.pokemonId }) {
            PokemonType(it.id, it.identifier, it.name)
        }
        val encounters = (dao.encounterMethods(game.versionId) + dao.staticPokemon(game.versionGroupId))
            .groupBy({ it.pokemonId }) { ObtainMethod.fromEncounterMethod(it.method) }
            .mapValues { (_, methods) -> methods.toSet() }
        val methods = obtainMethods(encounters, dao.evolutions(game.versionGroupId).map { it.fromId to it.toId })
        return dao.pokedex(game.versionGroupId, selected.id).map { row ->
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
