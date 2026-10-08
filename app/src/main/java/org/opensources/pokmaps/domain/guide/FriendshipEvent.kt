package org.opensources.pokmaps.domain.guide

enum class FriendshipEvent(val low: Int, val medium: Int, val high: Int) {
    LEVEL(5, 3, 2),
    VITAMIN(5, 3, 2),
    X_ITEM(1, 1, 0),
    GYM_BATTLE(3, 2, 1),
    LEARN_MOVE(1, 1, 0),
    FAINT(-1, -1, -1),
    POISON_FAINT(-5, -5, -10),
    STRONG_ENEMY_FAINT(-5, -5, -10),
    BITTER_POWDER(-5, -5, -10),
    ENERGY_ROOT(-10, -10, -15),
    REVIVAL_HERB(-15, -15, -20),
    GROOMING(3, 3, 1),
    LEVEL_AT_CAPTURE_PLACE(10, 6, 4);

    fun delta(value: Int): Int {
        require(value in 0..255)
        return when (value) {
            in 0..99 -> low
            in 100..199 -> medium
            in 200..255 -> high
            else -> error("Bonheur hors limites")
        }
    }

    fun apply(value: Int): Int = (value + delta(value)).coerceIn(0, 255)
}
