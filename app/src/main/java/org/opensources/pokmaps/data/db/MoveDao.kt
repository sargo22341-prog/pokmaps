package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface MoveDao {
    /** Attaque dans le jeu : caractéristiques, effet et CT / CS qui l'enseigne (null si elle n'existe pas). */
    @Query(
        """
        SELECT m.id, m.name_fr AS name, mv.power, mv.accuracy, mv.pp, mv.damage_class AS damageClass,
            mv.effect_fr AS effect, mv.effect_chance AS effectChance,
            t.id AS typeId, t.identifier AS typeIdentifier, t.name_fr AS typeName,
            i.identifier AS machineIdentifier, i.name_fr AS machineName
        FROM move m
        JOIN move_version_group mv ON mv.move_id = m.id AND mv.version_group_id = :versionGroupId
        JOIN type t ON t.id = mv.type_id
        LEFT JOIN machine ma ON ma.move_id = m.id AND ma.version_group_id = :versionGroupId
        LEFT JOIN item i ON i.id = ma.item_id
        WHERE m.id = :moveId
        """
    )
    suspend fun move(moveId: Int, versionGroupId: Int): MoveRow?

    /** Pokémon qui apprennent l'attaque dans le jeu, en montant de niveau ou par CT / CS. */
    @Query(
        """
        SELECT p.id AS pokemonId, p.name_fr AS name, pm.method, pm.level
        FROM pokemon_move pm JOIN pokemon p ON p.id = pm.pokemon_id
        WHERE pm.move_id = :moveId AND pm.version_group_id = :versionGroupId
            AND pm.method IN ('level-up', 'machine')
        ORDER BY pm.level, p.id
        """
    )
    suspend fun learners(moveId: Int, versionGroupId: Int): List<MoveLearnerRow>
}
