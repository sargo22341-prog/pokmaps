package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.domain.guide.BreedingCatalog
import org.opensources.pokmaps.domain.guide.BreedingPair
import org.opensources.pokmaps.domain.guide.BreedingRules
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.model.Game

interface BreedingTools {
    fun observe(): Flow<BreedingCatalog>
    suspend fun pair(game: Game, firstId: Int, secondId: Int, firstSex: ParentSex): BreedingPair
}

class BreedingUseCase @Inject constructor(
    private val games: GameRepository,
    private val pokedex: PokedexRepository,
    private val pokemon: PokemonRepository
) : BreedingTools {
    override fun observe(): Flow<BreedingCatalog> = games.selectedGame.map {
        if (it.generationId in 2..3) {
            val national = pokedex.catalogs(it).last().id
            BreedingCatalog(it, pokedex.pokedex(it, national), pokemon.breedingProfiles(it))
        } else {
            BreedingCatalog(it, emptyList())
        }
    }.flowOn(Dispatchers.IO)

    override suspend fun pair(game: Game, firstId: Int, secondId: Int, firstSex: ParentSex): BreedingPair =
        withContext(Dispatchers.IO) {
            require(game.generationId in 2..3)
            val first = requireNotNull(pokemon.details(game, firstId))
            val second = requireNotNull(pokemon.details(game, secondId))
            val mother = when {
                first.id == BreedingRules.DITTO -> second
                second.id == BreedingRules.DITTO -> first
                firstSex == ParentSex.FEMALE -> first
                else -> second
            }
            val root = requireNotNull(mother.evolutions.singleOrNull())
            val ids = when (root.pokemonId) {
                29 -> listOf(29, 32)
                314 -> if (game.generationId == 3) listOf(314, 313) else listOf(314)
                298 -> listOf(298, 183)
                360 -> listOf(360, 202)
                else -> listOf(root.pokemonId)
            }
            val babies = ids.map { requireNotNull(pokemon.details(game, it)) }
            BreedingPair(first, second, babies, game.generationId)
        }
}
