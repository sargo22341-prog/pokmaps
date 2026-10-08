package org.opensources.pokmaps.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

/**
 * Base pré-remplie générée par tools/build_data.py (assets/database/pokedex.db), en lecture seule.
 * VERSION doit être égale à SCHEMA_VERSION (tools/pokemaps_data/builder.py).
 */
@Database(
    entities = [
        GenerationEntity::class,
        RegionEntity::class,
        VersionGroupEntity::class,
        VersionEntity::class,
        PokedexEntity::class,
        VersionGroupPokedexEntity::class,
        PokedexEntryEntity::class,
        TypeEntity::class,
        TypeEfficacyEntity::class,
        StatEntity::class,
        GrowthRateEntity::class,
        PokemonEntity::class,
        PokemonTypeEntity::class,
        PokemonStatEntity::class,
        MoveEntity::class,
        MoveVersionGroupEntity::class,
        ItemEntity::class,
        MachineEntity::class,
        PokemonMoveEntity::class,
        PokemonItemEntity::class,
        EggGroupEntity::class,
        PokemonEggGroupEntity::class,
        AbilityEntity::class,
        AbilityVersionGroupEntity::class,
        PokemonAbilityEntity::class,
        EvolutionEntity::class,
        LocationEntity::class,
        LocationAreaEntity::class,
        EncounterMethodEntity::class,
        EncounterConditionValueEntity::class,
        EncounterEntity::class,
        EncounterConditionEntity::class,
        EncounterRateEntity::class,
        MapEntity::class,
        MapAreaEntity::class,
        MapWarpEntity::class,
        MapObjectEntity::class,
        TrainerPokemonEntity::class,
        NpcOfferEntity::class,
        MapSpotEntity::class
    ],
    version = PokedexDatabase.VERSION,
    exportSchema = true
)
abstract class PokedexDatabase : RoomDatabase() {
    abstract fun gameDao(): GameDao

    abstract fun pokedexDao(): PokedexDao

    abstract fun mapDao(): MapDao

    abstract fun pokemonDao(): PokemonDao

    abstract fun moveDao(): MoveDao

    companion object {
        const val VERSION = 11
        const val NAME = "pokedex.db"
        const val ASSET = "database/pokedex.db"
    }
}
