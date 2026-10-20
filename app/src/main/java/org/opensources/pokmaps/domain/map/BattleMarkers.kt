package org.opensources.pokmaps.domain.map

import kotlin.math.abs

/** Une seule enseigne pour les classes qui représentent deux partenaires du même combat. */
object BattleMarkers {
    data class Position(val objectId: Int, val x: Int, val y: Int)

    fun positions(objects: List<MapObject>, compactSprites: Boolean = false): List<Position> {
        val offset = if (compactSprites) 8 else 16
        val trainers = objects.filter { it.kind == MapObjectKind.TRAINER }
        val paired = mutableSetOf<Int>()
        return buildList {
            for (trainer in trainers) {
                if (trainer.id in paired) continue
                val partners = if (trainer.trainerClass in DUO_CLASSES || trainer.sprite in PARTNER_SPRITES) {
                    objects.filter { other ->
                        other.id != trainer.id && other.id !in paired && other.mapId == trainer.mapId &&
                            isPartner(trainer, other) &&
                            abs(other.x - trainer.x) + abs(other.y - trainer.y) in 1..32
                    }
                } else {
                    emptyList()
                }
                val partner = partners.singleOrNull()
                if (partner == null) {
                    add(Position(trainer.id, trainer.x + offset, trainer.y - offset))
                } else {
                    paired.add(partner.id)
                    add(Position(trainer.id, (trainer.x + partner.x) / 2, minOf(trainer.y, partner.y) - offset))
                }
            }
        }
    }

    private fun isPartner(trainer: MapObject, other: MapObject): Boolean {
        val sameDuo = trainer.trainerClass in DUO_CLASSES && trainer.trainerClass == other.trainerClass &&
            trainer.name == other.name
        val twinNpc = trainer.trainerClass == "twins" && other.kind == MapObjectKind.NPC && other.sprite == "twin"
        return sameDuo || twinNpc || PARTNER_SPRITES[trainer.sprite]?.contains(other.sprite) == true
    }

    private val PARTNER_SPRITES = mapOf(
        "obj-event-gfx-tate" to setOf("obj-event-gfx-liza"),
        "jessie" to setOf("james")
    )

    private val DUO_CLASSES = setOf(
        "twins",
        "young_couple",
        "double_team",
        "sis_and_bro",
        "interviewers",
        "TRAINER_CLASS_TWINS",
        "TRAINER_CLASS_SIS_AND_BRO",
        "TRAINER_CLASS_YOUNG_COUPLE",
        "TRAINER_CLASS_OLD_COUPLE",
        "TRAINER_CLASS_COOL_COUPLE",
        "TRAINER_CLASS_SR_AND_JR",
        "TRAINER_CLASS_INTERVIEWER"
    )
}
