package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.MoveDao
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.Machine
import org.opensources.pokmaps.domain.pokemon.MoveDetails
import org.opensources.pokmaps.domain.pokemon.MoveEffect
import org.opensources.pokmaps.domain.pokemon.MoveLearner

@Singleton
class MoveRepository @Inject constructor(private val dao: MoveDao) {
    /** Fiche de l'attaque dans le jeu, null si le jeu ne la connaît pas. */
    suspend fun details(game: Game, moveId: Int): MoveDetails? {
        val row = dao.move(moveId, game.versionGroupId) ?: return null
        val machine = if (row.machineIdentifier != null && row.machineName != null) {
            Machine(row.machineIdentifier, row.machineName)
        } else {
            null
        }
        return MoveDetails(
            id = row.id,
            name = row.name,
            type = PokemonType(row.typeId, row.typeIdentifier, row.typeName),
            damageClass = DamageClass.from(row.damageClass),
            power = row.power,
            accuracy = row.accuracy,
            pp = row.pp,
            effect = MoveEffect(row.effect, row.effectChance),
            machine = machine,
            learners = dao.learners(moveId, game.versionGroupId).map {
                MoveLearner(it.pokemonId, it.name, level = if (it.method == LEVEL_UP) it.level else null)
            }
        )
    }

    private companion object {
        const val LEVEL_UP = "level-up"
    }
}
