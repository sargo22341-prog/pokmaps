package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokedex.PokedexCatalog
import org.opensources.pokmaps.domain.pokedex.obtainMethods

@Singleton
class PokedexRepository @Inject constructor(private val dao: PokedexDao) {
    // Un seul contexte retenu par référentiel ; la base embarquée est immuable.
    private val references = Mutex()
    private var catalogReference: Pair<Int, List<PokedexCatalog>>? = null
    private var pokemonTypeReference: Pair<Int, Map<Int, List<PokemonType>>>? = null
    private var methodReference: Pair<Pair<Int, Int>, Map<Int, Set<ObtainMethod>>>? = null
    private var typeReference: Pair<Int, List<PokemonType>>? = null

    suspend fun catalogs(game: Game): List<PokedexCatalog> = references.withLock {
        catalogReference?.takeIf { it.first == game.versionGroupId }?.second
            ?: dao.catalogs(game.versionGroupId).map { PokedexCatalog(it.id, it.name) }
                .also { catalogReference = game.versionGroupId to it }
    }

    /** Pokédex choisi, régional par défaut, avec les façons d’obtenir chaque Pokémon dans la version. */
    suspend fun pokedex(game: Game, pokedexId: Int? = null): List<PokedexEntry> {
        val catalogs = catalogs(game)
        val selected = if (pokedexId == null) catalogs.firstOrNull() else catalogs.firstOrNull { it.id == pokedexId }
        checkNotNull(selected) { "Pokédex absent du jeu ${game.versionIdentifier} : $pokedexId" }
        val types = pokemonTypes(game)
        val methods = methods(game)
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

    private suspend fun pokemonTypes(game: Game): Map<Int, List<PokemonType>> = references.withLock {
        pokemonTypeReference?.takeIf { it.first == game.generationId }?.second
            ?: dao.pokemonTypes(game.generationId).groupBy({ it.pokemonId }) {
                PokemonType(it.id, it.identifier, it.name)
            }.also { pokemonTypeReference = game.generationId to it }
    }

    private suspend fun methods(game: Game): Map<Int, Set<ObtainMethod>> = references.withLock {
        val context = game.versionId to game.versionGroupId
        methodReference?.takeIf { it.first == context }?.second ?: run {
            val encounters = (dao.encounterMethods(game.versionId) + dao.staticPokemon(game.versionGroupId))
                .groupBy({ it.pokemonId }) { ObtainMethod.fromEncounterMethod(it.method) }
                .mapValues { (_, methods) -> methods.toSet() }
            obtainMethods(encounters, dao.evolutions(game.versionGroupId).map { it.fromId to it.toId })
                .also { methodReference = context to it }
        }
    }

    suspend fun types(game: Game): List<PokemonType> = references.withLock {
        typeReference?.takeIf { it.first == game.generationId }?.second
            ?: dao.types(game.generationId).map { PokemonType(it.id, it.identifier, it.name) }
                .also { typeReference = game.generationId to it }
    }
}
