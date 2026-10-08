package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface PokemonDao {
    @Query(
        """
        SELECT DISTINCT p.id AS pokemonId, p.gender_rate AS genderRate, eg.name_fr AS groupName
        FROM pokemon p
        JOIN pokedex_entry pe ON pe.pokemon_id = p.id
        JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
        LEFT JOIN pokemon_egg_group peg ON peg.pokemon_id = p.id
        LEFT JOIN egg_group eg ON eg.id = peg.egg_group_id
        WHERE vgp.version_group_id = :versionGroupId
        ORDER BY p.id, eg.id
        """
    )
    suspend fun breedingProfiles(versionGroupId: Int): List<BreedingRow>

    @Query(
        """
        SELECT p.id, p.name_fr AS name, p.name_en AS nameEn, p.genus_fr AS genus, p.description_fr AS description,
            p.height_dm AS heightDm, p.weight_hg AS weightHg, p.capture_rate AS captureRate,
            g.name_fr AS growthRate, p.evolution_chain_id AS evolutionChainId, p.gender_rate AS genderRate,
            p.hatch_counter AS hatchCounter
        FROM pokemon p JOIN growth_rate g ON g.id = p.growth_rate_id
        WHERE p.id = :pokemonId
        """
    )
    suspend fun pokemon(pokemonId: Int): PokemonRow?

    @Query(
        """
        SELECT min(pe.number) FROM pokedex_entry pe
        JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
        WHERE vgp.version_group_id = :versionGroupId AND pe.pokemon_id = :pokemonId
        """
    )
    suspend fun number(pokemonId: Int, versionGroupId: Int): Int?

    @Query(
        """
        SELECT t.id, t.identifier, t.name_fr AS name
        FROM pokemon_type pt JOIN type t ON t.id = pt.type_id
        WHERE pt.pokemon_id = :pokemonId AND pt.generation_id = :generationId
        ORDER BY pt.slot
        """
    )
    suspend fun types(pokemonId: Int, generationId: Int): List<TypeRow>

    /** Stats de base : Spécial en première génération, Atq. Spé. et Déf. Spé. à partir de la deuxième. */
    @Query(
        """
        SELECT s.identifier, s.name_fr AS name, ps.base_stat AS value
        FROM pokemon_stat ps JOIN stat s ON s.id = ps.stat_id
        WHERE ps.pokemon_id = :pokemonId AND ps.generation_id = :generationId
        ORDER BY s.id
        """
    )
    suspend fun stats(pokemonId: Int, generationId: Int): List<StatRow>

    @Query(
        """
        SELECT attacking_type_id AS attackingTypeId, defending_type_id AS defendingTypeId, damage_factor AS factor
        FROM type_efficacy WHERE generation_id = :generationId
        """
    )
    suspend fun typeFactors(generationId: Int): List<TypeFactorRow>

    @Query("SELECT id, name_fr AS name FROM pokemon WHERE evolution_chain_id = :chainId ORDER BY id")
    suspend fun chainMembers(chainId: Int): List<ChainMemberRow>

    @Query(
        """
        SELECT e.from_pokemon_id AS fromId, e.to_pokemon_id AS toId, e.`trigger` AS `trigger`, e.min_level AS minLevel,
            coalesce(i.name_fr, hi.name_fr) AS itemName, coalesce(i.identifier, hi.identifier) AS itemIdentifier,
            coalesce(i.has_sprite, hi.has_sprite) AS itemHasSprite, e.min_happiness AS minHappiness,
            e.time_of_day AS timeOfDay
        FROM evolution e
        JOIN pokemon p ON p.id = e.from_pokemon_id
        LEFT JOIN item i ON i.id = e.item_id
        LEFT JOIN item hi ON hi.id = e.held_item_id
        WHERE e.version_group_id = :versionGroupId AND p.evolution_chain_id = :chainId
        """
    )
    suspend fun evolutions(chainId: Int, versionGroupId: Int): List<EvolutionRow>

    /** Attaques par niveau, CT/CS, œuf et tuteur, avec leurs caractéristiques dans le jeu. */
    @Query(
        """
        SELECT pm.method, pm.level, m.id AS moveId, m.name_fr AS name, mv.power, mv.accuracy, mv.pp,
            mv.damage_class AS damageClass, t.id AS typeId, t.identifier AS typeIdentifier, t.name_fr AS typeName,
            i.name_fr AS machine, i.identifier AS machineIdentifier
        FROM pokemon_move pm
        JOIN move m ON m.id = pm.move_id
        JOIN move_version_group mv ON mv.move_id = pm.move_id AND mv.version_group_id = pm.version_group_id
        JOIN type t ON t.id = mv.type_id
        LEFT JOIN machine ma ON pm.method = 'machine' AND ma.move_id = pm.move_id
            AND ma.version_group_id = pm.version_group_id
        LEFT JOIN item i ON i.id = ma.item_id
        WHERE pm.pokemon_id = :pokemonId AND pm.version_group_id = :versionGroupId
            AND pm.method IN ('level-up', 'machine', 'egg', 'tutor')
        """
    )
    suspend fun moves(pokemonId: Int, versionGroupId: Int): List<LearnedMoveRow>

    /** Rencontres du Pokémon dans toutes les versions. */
    @Query(
        """
        SELECT $ENCOUNTER_COLUMNS FROM $ENCOUNTER_TABLES
        WHERE e.pokemon_id = :pokemonId
        """
    )
    suspend fun encounters(pokemonId: Int): List<EncounterRow>

    @Query(
        """
        SELECT count(*) FROM map_object o JOIN map m ON m.id = o.map_id
        WHERE o.kind = 'pokemon' AND o.pokemon_id = :pokemonId AND m.version_group_id = :versionGroupId
        """
    )
    suspend fun staticCount(pokemonId: Int, versionGroupId: Int): Int

    /** Objets que tient le Pokémon sauvage dans la version, du plus fréquent au plus rare. */
    @Query(
        """
        SELECT i.identifier, i.name_fr AS name, i.has_sprite AS hasSprite, pi.rarity
        FROM pokemon_item pi JOIN item i ON i.id = pi.item_id
        WHERE pi.pokemon_id = :pokemonId AND pi.version_id = :versionId
        ORDER BY pi.rarity DESC, i.name_fr
        """
    )
    suspend fun heldItems(pokemonId: Int, versionId: Int): List<HeldItemRow>

    @Query(
        """
        SELECT eg.name_fr FROM pokemon_egg_group peg JOIN egg_group eg ON eg.id = peg.egg_group_id
        WHERE peg.pokemon_id = :pokemonId ORDER BY eg.id
        """
    )
    suspend fun eggGroups(pokemonId: Int): List<String>

    /** Talents de la génération, avec leur description dans le jeu. */
    @Query(
        """
        SELECT a.name_fr AS name, av.description_fr AS description, pa.is_hidden AS hidden
        FROM pokemon_ability pa JOIN ability a ON a.id = pa.ability_id
        LEFT JOIN ability_version_group av ON av.ability_id = a.id AND av.version_group_id = :versionGroupId
        WHERE pa.pokemon_id = :pokemonId AND pa.generation_id = :generationId
        ORDER BY pa.slot
        """
    )
    suspend fun abilities(pokemonId: Int, generationId: Int, versionGroupId: Int): List<AbilityRow>
}

const val ENCOUNTER_COLUMNS = """
    e.version_id AS versionId, v.name_fr AS versionName, e.location_area_id AS areaId, la.name_fr AS areaName,
    e.pokemon_id AS pokemonId, p.name_fr AS pokemonName, m.identifier AS method, m.name_fr AS methodName,
    m.sort_order AS methodOrder, m.is_one_off AS isOneOff, e.min_level AS minLevel, e.max_level AS maxLevel,
    e.chance, e.quantity, e.note_fr AS note,
    (SELECT group_concat(cv.name_fr, ', ') FROM encounter_condition ec
        JOIN encounter_condition_value cv ON cv.id = ec.condition_value_id WHERE ec.encounter_id = e.id) AS conditions,
    (SELECT group_concat(cv.identifier, ',') FROM encounter_condition ec
        JOIN encounter_condition_value cv ON cv.id = ec.condition_value_id
        WHERE ec.encounter_id = e.id) AS conditionIdentifiers,
    (SELECT group_concat(cv.name_fr, ', ') FROM encounter_condition ec
        JOIN encounter_condition_value cv ON cv.id = ec.condition_value_id
        WHERE ec.encounter_id = e.id AND cv.identifier NOT IN ('time-morning', 'time-day', 'time-night'))
        AS nonTimeConditions
"""

const val ENCOUNTER_TABLES = """
    encounter e
    JOIN version v ON v.id = e.version_id
    JOIN location_area la ON la.id = e.location_area_id
    JOIN pokemon p ON p.id = e.pokemon_id
    JOIN encounter_method m ON m.id = e.method_id
"""
