package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Test

class BattleMarkersTest {
    private val trainer = MapObject(
        1, 1, MapObjectKind.TRAINER, 40, 56, "obj-event-gfx-twin", null,
        null, null, null, null, null, "TRAINER_CLASS_TWINS", "Jumelles"
    )

    @Test
    fun singleBattleIsAboveAndRightOfTheSprite() {
        assertEquals(listOf(BattleMarkers.Position(1, 56, 40)), BattleMarkers.positions(listOf(trainer)))
    }

    @Test
    fun gameBoyDuoSharesAnIconWithItsNpcPartner() {
        val classic = trainer.copy(sprite = "twin", trainerClass = "twins")
        val partner = classic.copy(id = 2, x = 56, kind = MapObjectKind.NPC, trainerClass = null)
        assertEquals(listOf(BattleMarkers.Position(1, 48, 40)), BattleMarkers.positions(listOf(classic, partner)))
    }

    @Test
    fun duoHasOneCenteredIconAboveBothSprites() {
        val partner = trainer.copy(id = 2, x = 56)
        assertEquals(listOf(BattleMarkers.Position(1, 48, 40)), BattleMarkers.positions(listOf(trainer, partner)))
    }

    @Test
    fun nearbyIndependentTrainersKeepTheirOwnIcons() {
        val first = trainer.copy(trainerClass = "TRAINER_CLASS_YOUNGSTER")
        assertEquals(2, BattleMarkers.positions(listOf(first, first.copy(id = 2, x = 56))).size)
    }

    @Test
    fun partnersOnDifferentMapsOrFarAwayAreSeparate() {
        assertEquals(2, BattleMarkers.positions(listOf(trainer, trainer.copy(id = 2, mapId = 2))).size)
        assertEquals(2, BattleMarkers.positions(listOf(trainer, trainer.copy(id = 2, x = 104))).size)
    }

    @Test
    fun namedPartnerWithoutTrainerTeamSharesTheIcon() {
        val tate = trainer.copy(sprite = "obj-event-gfx-tate", trainerClass = "TRAINER_CLASS_LEADER")
        val liza = trainer.copy(id = 2, x = 56, kind = MapObjectKind.NPC, sprite = "obj-event-gfx-liza")
        assertEquals(listOf(BattleMarkers.Position(1, 48, 40)), BattleMarkers.positions(listOf(tate, liza)))
    }

    @Test
    fun emptyAndNonTrainerListsHaveNoBattleIcon() {
        assertEquals(emptyList<BattleMarkers.Position>(), BattleMarkers.positions(emptyList()))
        assertEquals(
            emptyList<BattleMarkers.Position>(),
            BattleMarkers.positions(listOf(trainer.copy(kind = MapObjectKind.NPC)))
        )
    }
}
