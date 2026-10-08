package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.EncounterRow
import org.opensources.pokmaps.data.db.LearnedMoveRow
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.domain.guide.BreedingProfile
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.BaseStat
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionEdge
import org.opensources.pokmaps.domain.pokemon.EvolutionTree
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.HeldItem
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.Machine
import org.opensources.pokmaps.domain.pokemon.PokemonAbility
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.domain.pokemon.PokemonTraits
import org.opensources.pokmaps.domain.pokemon.TypeChart

@Singleton
class PokemonRepository @Inject constructor(private val dao: PokemonDao, private val pokedex: PokedexRepository) {
    suspend fun breedingProfiles(game: Game): Map<Int, BreedingProfile> =
        dao.breedingProfiles(game.versionGroupId).groupBy { it.pokemonId }.mapValues { (id, rows) ->
            BreedingProfile(
                id,
                GenderRatio.from(rows.first().genderRate),
                rows.mapNotNull { it.groupName }.toSet()
            )
        }

    suspend fun details(game: Game, pokemonId: Int): PokemonDetails? {
        val pokemon = dao.pokemon(pokemonId) ?: return null
        val types = dao.types(pokemonId, game.generationId).map { PokemonType(it.id, it.identifier, it.name) }
        val factors = dao.typeFactors(game.generationId).associate {
            (it.attackingTypeId to it.defendingTypeId) to
                it.factor
        }
        val moves = dao.moves(pokemonId, game.versionGroupId).groupBy { it.method }
        return PokemonDetails(
            id = pokemon.id,
            number = dao.number(pokemonId, game.versionGroupId),
            name = pokemon.name,
            nameEn = pokemon.nameEn,
            genus = pokemon.genus,
            description = pokemon.description,
            heightDm = pokemon.heightDm,
            weightHg = pokemon.weightHg,
            captureRate = pokemon.captureRate,
            growthRate = pokemon.growthRate,
            types = types,
            stats = dao.stats(pokemonId, game.generationId).map { BaseStat(it.identifier, it.name, it.value) },
            weaknesses = TypeChart.defensive(pokedex.types(game), types.map { it.id }, factors),
            evolutions = evolutions(game, pokemon.evolutionChainId),
            levelUpMoves = moves["level-up"].orEmpty().map {
                it.toLearnedMove()
            }.sortedWith(compareBy({ it.level }, { it.name })),
            machineMoves = moves["machine"].orEmpty().map { it.toLearnedMove() }
                .sortedWith(compareBy({ it.machine?.isHm }, { it.machine?.name })),
            encounters = dao.encounters(pokemonId).map { it.toEncounter() },
            staticEncounters = dao.staticCount(pokemonId, game.versionGroupId),
            traits = traits(game, pokemonId, pokemon.genderRate, pokemon.hatchCounter),
            eggMoves = moves["egg"].orEmpty().map { it.toLearnedMove() }.sortedBy { it.name },
            tutorMoves = moves["tutor"].orEmpty().map { it.toLearnedMove() }.sortedBy { it.name }
        )
    }

    private suspend fun evolutions(
        game: Game,
        chainId: Int
    ): List<org.opensources.pokmaps.domain.pokemon.EvolutionNode> {
        val members = dao.chainMembers(chainId).associate { it.id to it.name }
        val edges = dao.evolutions(chainId, game.versionGroupId).map {
            EvolutionEdge(
                it.fromId,
                it.toId,
                EvolutionCondition(
                    it.trigger,
                    it.minLevel,
                    it.itemName,
                    it.itemIdentifier,
                    it.itemHasSprite == true,
                    it.minHappiness,
                    it.timeOfDay
                )
            )
        }
        return EvolutionTree.build(members, edges)
    }

    /** Objets tenus, sexe, œufs et talents : vides pour un jeu qui ne les connaît pas (base sans ces données). */
    private suspend fun traits(game: Game, pokemonId: Int, genderRate: Int, hatchCounter: Int) = PokemonTraits(
        heldItems = dao.heldItems(pokemonId, game.versionId).map {
            HeldItem(it.identifier, it.name, it.hasSprite, it.rarity)
        },
        gender = GenderRatio.from(genderRate),
        eggGroups = dao.eggGroups(pokemonId),
        hatchCycles = hatchCounter,
        abilities = dao.abilities(pokemonId, game.generationId, game.versionGroupId).map {
            PokemonAbility(it.name, it.description, it.hidden)
        }
    )

    private fun LearnedMoveRow.toLearnedMove() = LearnedMove(
        moveId = moveId,
        name = name,
        type = PokemonType(typeId, typeIdentifier, typeName),
        damageClass = DamageClass.from(damageClass),
        power = power,
        accuracy = accuracy,
        pp = pp,
        level = level,
        machine = if (method == MACHINE) {
            Machine(
                checkNotNull(machineIdentifier) { "CT/CS absente pour l'attaque $moveId" },
                checkNotNull(machine) { "CT/CS absente pour l'attaque $moveId" }
            )
        } else {
            null
        }
    )

    private companion object {
        const val MACHINE = "machine"
    }
}

fun EncounterRow.toEncounter() = Encounter(
    versionId = versionId,
    versionName = versionName,
    areaId = areaId,
    areaName = areaName,
    pokemonId = pokemonId,
    pokemonName = pokemonName,
    method = method,
    methodName = methodName,
    methodOrder = methodOrder,
    isOneOff = isOneOff,
    minLevel = minLevel,
    maxLevel = maxLevel,
    chance = chance,
    quantity = quantity,
    note = note,
    conditions = conditions,
    nonTimeConditions = nonTimeConditions,
    times = conditionIdentifiers.orEmpty().split(',').mapNotNull(EncounterTime::fromCondition).toSet()
)
