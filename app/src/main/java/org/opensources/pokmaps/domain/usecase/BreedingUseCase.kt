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
import org.opensources.pokmaps.domain.pokemon.GenerationFeature

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
        if (GenerationFeature.BREEDING.existsIn(it.generationId)) {
            val national = pokedex.catalogs(it).last().id
            BreedingCatalog(it, pokedex.pokedex(it, national), pokemon.breedingProfiles(it))
        } else {
            BreedingCatalog(it, emptyList())
        }
    }.flowOn(Dispatchers.IO)

    override suspend fun pair(game: Game, firstId: Int, secondId: Int, firstSex: ParentSex): BreedingPair =
        withContext(Dispatchers.IO) {
            require(GenerationFeature.BREEDING.existsIn(game.generationId))
            val first = requireNotNull(pokemon.details(game, firstId))
            val second = requireNotNull(pokemon.details(game, secondId))
            val mother = when {
                first.id == BreedingRules.DITTO -> second
                second.id == BreedingRules.DITTO -> first
                firstSex == ParentSex.FEMALE -> first
                else -> second
            }
            // Manaphy et Phione partagent une famille PokéAPI sans lien d’évolution.
            val root = if (mother.id in
                489..490
            ) {
                mother.id
            } else {
                requireNotNull(mother.evolutions.singleOrNull()).pokemonId
            }
            val ids = when (root) {
                29 -> listOf(29, 32)
                314 -> listOf(314, 313)
                298 -> listOf(298, 183)
                360 -> listOf(360, 202)
                406 -> listOf(406, 315)
                433 -> listOf(433, 358)
                438 -> listOf(438, 185)
                439 -> listOf(439, 122)
                440 -> listOf(440, 113)
                446 -> listOf(446, 143)
                458 -> listOf(458, 226)
                490 -> listOf(489)
                else -> listOf(root)
            }
            val babies = ids.map { requireNotNull(pokemon.details(game, it)) }
            BreedingPair(first, second, babies, game.generationId)
        }
}
