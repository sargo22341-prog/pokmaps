package org.opensources.pokmaps.domain.guide

/** Différences vérifiées dans get_egg.c du moteur HGSS épinglé. */
object HgssBreeding {
    fun babies(pair: BreedingPair, first: ParentValues, second: ParentValues) = DsBreeding.babies(pair, first, second)

    fun inherited(
        child: org.opensources.pokmaps.domain.pokemon.PokemonDetails,
        donor: List<Int>,
        other: List<Int>,
        lightBall: Boolean
    ) = DsBreeding.inherited(child, donor, other, lightBall)

    val powerItems: Map<BreedingItem, BreedingIv> = mapOf(
        BreedingItem.POWER_WEIGHT to BreedingIv.HP,
        BreedingItem.POWER_BRACER to BreedingIv.ATTACK,
        BreedingItem.POWER_BELT to BreedingIv.DEFENSE,
        BreedingItem.POWER_ANKLET to BreedingIv.SPEED,
        BreedingItem.POWER_LENS to BreedingIv.SPECIAL_ATTACK,
        BreedingItem.POWER_BAND to BreedingIv.SPECIAL_DEFENSE
    )

    fun natureParents(first: ParentValues, second: ParentValues): List<Int> =
        listOf(first, second).mapIndexedNotNull { index, parent ->
            index.takeIf { parent.item == BreedingItem.EVERSTONE }
        }

    /** Deux objets proposent deux alternatives ; un seul IV forcé compte parmi les trois hérités. */
    fun forcedIvs(first: ParentValues, second: ParentValues): List<ForcedBreedingIv> =
        listOf(first, second).mapIndexedNotNull { index, parent ->
            powerItems[parent.item]?.let { stat -> ForcedBreedingIv(index, stat, parent.ivs[stat.ordinal]) }
        }
}

data class ForcedBreedingIv(val parent: Int, val stat: BreedingIv, val value: Int?)
