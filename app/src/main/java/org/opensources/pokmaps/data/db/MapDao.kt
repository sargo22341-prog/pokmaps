package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface MapDao {
    @Query("SELECT * FROM map WHERE version_group_id = :versionGroupId ORDER BY id")
    suspend fun maps(versionGroupId: Int): List<MapEntity>

    @Query(
        """
        SELECT w.* FROM map_warp w JOIN map m ON m.id = w.map_id
        WHERE m.version_group_id = :versionGroupId ORDER BY w.id
        """
    )
    suspend fun warps(versionGroupId: Int): List<MapWarpEntity>

    @Query(
        """
        SELECT o.id, o.map_id AS mapId, o.kind, o.x, o.y, o.sprite, o.item_id AS itemId,
            i.identifier AS itemIdentifier, i.name_fr AS itemName, o.pokemon_id AS pokemonId,
            p.name_fr AS pokemonName, o.level, o.trainer_class AS trainerClass
        FROM map_object o
        JOIN map m ON m.id = o.map_id
        LEFT JOIN item i ON i.id = o.item_id
        LEFT JOIN pokemon p ON p.id = o.pokemon_id
        WHERE m.version_group_id = :versionGroupId
        ORDER BY o.id
        """
    )
    suspend fun objects(versionGroupId: Int): List<MapObjectRow>

    @Query(
        """
        SELECT ma.map_id AS mapId, ma.location_area_id AS areaId, la.name_fr AS name
        FROM map_area ma
        JOIN map m ON m.id = ma.map_id
        JOIN location_area la ON la.id = ma.location_area_id
        WHERE m.version_group_id = :versionGroupId
        ORDER BY ma.map_id, la.id
        """
    )
    suspend fun areas(versionGroupId: Int): List<MapAreaRow>

    /** Rencontres des zones d'un lieu dans une version. */
    @Query(
        "SELECT $ENCOUNTER_COLUMNS FROM $ENCOUNTER_TABLES WHERE e.version_id = :versionId AND e.location_area_id IN (:areaIds)"
    )
    suspend fun encounters(versionId: Int, areaIds: List<Int>): List<EncounterRow>

    /** Zones où l'on rencontre un Pokémon dans une version. */
    @Query("SELECT DISTINCT location_area_id FROM encounter WHERE version_id = :versionId AND pokemon_id = :pokemonId")
    suspend fun pokemonAreas(versionId: Int, pokemonId: Int): List<Int>

    @Query(
        """
        SELECT s.* FROM map_spot s JOIN map m ON m.id = s.map_id
        WHERE m.version_group_id = :versionGroupId ORDER BY s.id
        """
    )
    suspend fun spots(versionGroupId: Int): List<MapSpotEntity>

    /** Équipe d'un dresseur de la carte. */
    @Query(
        """
        SELECT t.slot, t.pokemon_id AS pokemonId, p.name_fr AS name, t.level
        FROM trainer_pokemon t JOIN pokemon p ON p.id = t.pokemon_id
        WHERE t.map_object_id = :objectId ORDER BY t.slot
        """
    )
    suspend fun trainerParty(objectId: Int): List<TrainerPokemonRow>

    /** Attaques de l'équipe d'un dresseur, avec leurs caractéristiques dans le jeu. */
    @Query(
        """
        SELECT t.slot, mv.move_slot AS moveSlot, m.id AS moveId, m.name_fr AS name, v.power, v.accuracy, v.pp,
            v.damage_class AS damageClass, ty.id AS typeId, ty.identifier AS typeIdentifier, ty.name_fr AS typeName
        FROM trainer_pokemon t
        JOIN (
            SELECT map_object_id, slot, 1 AS move_slot, move1_id AS move_id FROM trainer_pokemon
            UNION ALL SELECT map_object_id, slot, 2, move2_id FROM trainer_pokemon
            UNION ALL SELECT map_object_id, slot, 3, move3_id FROM trainer_pokemon
            UNION ALL SELECT map_object_id, slot, 4, move4_id FROM trainer_pokemon
        ) mv ON mv.map_object_id = t.map_object_id AND mv.slot = t.slot
        JOIN move m ON m.id = mv.move_id
        JOIN move_version_group v ON v.move_id = m.id AND v.version_group_id = :versionGroupId
        JOIN type ty ON ty.id = v.type_id
        WHERE t.map_object_id = :objectId
        ORDER BY t.slot, mv.move_slot
        """
    )
    suspend fun trainerMoves(objectId: Int, versionGroupId: Int): List<TrainerMoveRow>

    /** Dons, ventes et échanges d'un personnage. */
    @Query(
        """
        SELECT n.kind, n.item_id AS itemId, i.identifier AS itemIdentifier, i.name_fr AS itemName,
            i.has_sprite AS itemHasSprite, n.pokemon_id AS pokemonId, p.name_fr AS pokemonName, n.quantity, n.price,
            n.wanted_pokemon_id AS wantedPokemonId, w.name_fr AS wantedPokemonName
        FROM npc_offer n
        LEFT JOIN item i ON i.id = n.item_id
        LEFT JOIN pokemon p ON p.id = n.pokemon_id
        LEFT JOIN pokemon w ON w.id = n.wanted_pokemon_id
        WHERE n.map_object_id = :objectId ORDER BY n.id
        """
    )
    suspend fun offers(objectId: Int): List<NpcOfferRow>

    /** Objet : description, ou attaque de la CT / CS dans le jeu. */
    @Query(
        """
        SELECT i.id, i.identifier, i.name_fr AS name, i.has_sprite AS hasSprite, i.description_fr AS description,
            m.name_fr AS moveName, v.power, v.accuracy, v.pp, v.damage_class AS damageClass,
            t.id AS typeId, t.identifier AS typeIdentifier, t.name_fr AS typeName
        FROM item i
        LEFT JOIN machine ma ON ma.item_id = i.id AND ma.version_group_id = :versionGroupId
        LEFT JOIN move m ON m.id = ma.move_id
        LEFT JOIN move_version_group v ON v.move_id = ma.move_id AND v.version_group_id = :versionGroupId
        LEFT JOIN type t ON t.id = v.type_id
        WHERE i.id = :itemId
        """
    )
    suspend fun item(itemId: Int, versionGroupId: Int): ItemDetailsRow?
}
