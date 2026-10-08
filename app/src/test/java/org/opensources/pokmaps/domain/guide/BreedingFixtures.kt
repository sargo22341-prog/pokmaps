package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.domain.pokemon.PokemonTraits

internal fun breedingPokemon(
    id: Int,
    groups: List<String> = listOf("Monstrueux"),
    gender: GenderRatio = GenderRatio.Gendered(1)
): PokemonDetails = PokemonDetails(
    id = id, number = id, name = "Espèce $id", nameEn = "Species $id", genus = "", description = null,
    heightDm = 0, weightHg = 0, captureRate = 45, growthRate = "", types = emptyList(), stats = emptyList(),
    weaknesses = emptyList(), evolutions = emptyList(), levelUpMoves = emptyList(), machineMoves = emptyList(),
    encounters = emptyList(), staticEncounters = 0,
    traits = PokemonTraits(emptyList(), gender, groups, 20, emptyList())
)
