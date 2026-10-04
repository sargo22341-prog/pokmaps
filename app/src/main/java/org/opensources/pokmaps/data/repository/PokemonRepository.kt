package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.EncounterRow
import org.opensources.pokmaps.data.db.LearnedMoveRow
import org.opensources.pokmaps.data.db.PokemonDao
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.BaseStat
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionEdge
import org.opensources.pokmaps.domain.pokemon.EvolutionTree
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.domain.pokemon.TypeChart

@Singleton
class PokemonRepository @Inject constructor(private val dao: PokemonDao, private val pokedex: PokedexRepository) {
    suspend fun details(game: Game, pokemonId: Int): PokemonDetails? {
        val pokemon = dao.pokemon(pokemonId) ?: return null
        val types = dao.types(pokemonId, game.generationId).map { PokemonType(it.id, it.identifier, it.name) }
        val factors = dao.typeFactors(game.generationId).associate {
            (it.attackingTypeId to it.defendingTypeId) to
                it.factor
        }
        val members = dao.chainMembers(pokemon.evolutionChainId).associate { it.id to it.name }
        val edges = dao.evolutions(pokemon.evolutionChainId, game.versionGroupId).map {
            EvolutionEdge(
                it.fromId,
                it.toId,
                EvolutionCondition(it.trigger, it.minLevel, it.itemName, it.itemIdentifier, it.itemHasSprite == true)
            )
        }
        val moves = dao.moves(pokemonId, game.versionGroupId).map { it.toLearnedMove() }
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
            evolutions = EvolutionTree.build(members, edges),
            levelUpMoves = moves.filter { it.machine == null }.sortedWith(compareBy({ it.level }, { it.name })),
            machineMoves = moves.filter { it.machine != null }.sortedWith(compareBy({ it.isHm() }, { it.machine })),
            encounters = dao.encounters(pokemonId).map { it.toEncounter() },
            staticEncounters = dao.staticCount(pokemonId, game.versionGroupId),
            spritePath = Sprites.pokemonSprite(game.versionGroupIdentifier, pokemonId),
            iconPath = Sprites.pokemonIcon(pokemonId)
        )
    }

    private fun LearnedMove.isHm() = machine?.startsWith("CS") == true

    private fun LearnedMoveRow.toLearnedMove() = LearnedMove(
        moveId = moveId,
        name = name,
        type = PokemonType(typeId, typeIdentifier, typeName),
        damageClass = DamageClass.from(damageClass),
        power = power,
        accuracy = accuracy,
        pp = pp,
        level = level,
        machine = if (method == "machine") machine ?: "CT/CS" else null
    )
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
    conditions = conditions
)
