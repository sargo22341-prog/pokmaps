package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup

enum class FriendshipRules {
    GOLD_SILVER,
    CRYSTAL,
    RUBY_SAPPHIRE,
    EMERALD,
    FIRERED_LEAFGREEN;

    val gba: Boolean get() = this in setOf(RUBY_SAPPHIRE, EMERALD, FIRERED_LEAFGREEN)

    val events: List<FriendshipEvent> get() = FriendshipEvent.entries.filter { event ->
        when (event) {
            FriendshipEvent.LEVEL_AT_CAPTURE_PLACE -> this == CRYSTAL

            FriendshipEvent.GROOMING -> !gba

            FriendshipEvent.WALKING -> gba

            FriendshipEvent.MASSAGE -> this == FIRERED_LEAFGREEN

            FriendshipEvent.EV_BERRY -> this == EMERALD

            FriendshipEvent.LEVEL, FriendshipEvent.VITAMIN, FriendshipEvent.X_ITEM,
            FriendshipEvent.GYM_BATTLE, FriendshipEvent.LEARN_MOVE, FriendshipEvent.FAINT,
            FriendshipEvent.POISON_FAINT, FriendshipEvent.STRONG_ENEMY_FAINT,
            FriendshipEvent.BITTER_POWDER, FriendshipEvent.ENERGY_ROOT, FriendshipEvent.REVIVAL_HERB -> true
        }
    }

    fun apply(
        event: FriendshipEvent,
        value: Int,
        sootheBell: Boolean,
        luxuryBall: Boolean,
        capturePlace: Boolean
    ): Int {
        require(event in events)
        var delta = event.delta(value)
        if (gba && delta > 0) {
            if (sootheBell) delta = delta * 150 / 100
            if (luxuryBall) delta++
            if (capturePlace) delta++
        }
        return (value + delta).coerceIn(0, 255)
    }

    companion object {
        fun forGame(game: Game): FriendshipRules = when (game.versionGroup) {
            VersionGroup.GOLD_SILVER -> GOLD_SILVER
            VersionGroup.CRYSTAL -> CRYSTAL
            VersionGroup.RUBY_SAPPHIRE -> RUBY_SAPPHIRE
            VersionGroup.EMERALD -> EMERALD
            VersionGroup.FIRERED_LEAFGREEN -> FIRERED_LEAFGREEN
            VersionGroup.RED_BLUE, VersionGroup.YELLOW -> error("Jeu sans outil de bonheur : ${game.versionIdentifier}")
        }
    }
}
