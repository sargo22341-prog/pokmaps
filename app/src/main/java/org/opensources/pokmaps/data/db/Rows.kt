package org.opensources.pokmaps.data.db

// Résultats de requêtes (jointures) : les noms des propriétés sont ceux des colonnes renvoyées.

data class PokedexRow(val number: Int, val pokemonId: Int, val name: String, val nameEn: String)

data class TypeRow(val id: Int, val identifier: String, val name: String)

data class PokemonTypeRow(val pokemonId: Int, val slot: Int, val id: Int, val identifier: String, val name: String)

data class PokemonMethodRow(val pokemonId: Int, val method: String)

data class EvolutionPairRow(val fromId: Int, val toId: Int)

data class TypeFactorRow(val attackingTypeId: Int, val defendingTypeId: Int, val factor: Int)

data class PokemonRow(
    val id: Int,
    val name: String,
    val nameEn: String,
    val genus: String,
    val description: String?,
    val heightDm: Int,
    val weightHg: Int,
    val captureRate: Int,
    val growthRate: String,
    val evolutionChainId: Int
)

data class StatRow(val identifier: String, val name: String, val value: Int)

data class ChainMemberRow(val id: Int, val name: String)

data class EvolutionRow(
    val fromId: Int,
    val toId: Int,
    val trigger: String,
    val minLevel: Int?,
    val itemName: String?,
    val itemIdentifier: String?,
    val itemHasSprite: Boolean?
)

data class LearnedMoveRow(
    val method: String,
    val level: Int,
    val moveId: Int,
    val name: String,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    val damageClass: String,
    val typeId: Int,
    val typeIdentifier: String,
    val typeName: String,
    val machine: String?,
    val machineIdentifier: String?
)

data class EncounterRow(
    val versionId: Int,
    val versionName: String,
    val areaId: Int,
    val areaName: String,
    val pokemonId: Int,
    val pokemonName: String,
    val method: String,
    val methodName: String,
    val methodOrder: Int,
    val isOneOff: Boolean,
    val minLevel: Int,
    val maxLevel: Int,
    val chance: Double?,
    val quantity: Int,
    val note: String?,
    val conditions: String?
)

data class MapObjectRow(
    val id: Int,
    val mapId: Int,
    val kind: String,
    val x: Int,
    val y: Int,
    val sprite: String?,
    val itemId: Int?,
    val itemIdentifier: String?,
    val itemName: String?,
    val pokemonId: Int?,
    val pokemonName: String?,
    val level: Int?,
    val trainerClass: String?
)

data class MapAreaRow(val mapId: Int, val areaId: Int, val name: String)
