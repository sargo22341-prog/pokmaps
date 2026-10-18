package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.GameVersion

/** Collection sans échange externe, événement ni duplication, selon les règles de chaque cartouche. */
object Gen3CaptureGoals {
    fun forVersion(version: Int): CaptureGoal {
        val available = when (GameVersion.of(version)) {
            GameVersion.RUBY -> RUBY

            GameVersion.SAPPHIRE -> SAPPHIRE

            GameVersion.EMERALD -> EMERALD

            GameVersion.FIRERED -> FIRERED

            GameVersion.LEAFGREEN -> LEAFGREEN

            GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW, GameVersion.GOLD, GameVersion.SILVER,
            GameVersion.CRYSTAL, GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error(
                "Version GBA inconnue : $version"
            )
        }
        val choices = when (GameVersion.of(version)) {
            GameVersion.RUBY -> listOf(HOENN_STARTERS, FOSSILS, MOON_STONE)

            GameVersion.SAPPHIRE -> listOf(HOENN_STARTERS, FOSSILS)

            GameVersion.EMERALD -> listOf(HOENN_STARTERS, MOON_STONE, singles(listOf(380, 381)))

            GameVersion.FIRERED, GameVersion.LEAFGREEN -> listOf(KANTO_STARTERS_AND_ROAMER, KANTO_FOSSILS)

            GameVersion.RED, GameVersion.BLUE, GameVersion.YELLOW, GameVersion.GOLD, GameVersion.SILVER,
            GameVersion.CRYSTAL, GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> error(
                "Version GBA inconnue : $version"
            )
        }
        val selectedChoices = choices.mapNotNull { choice ->
            val options = choice.alternatives.map { it.intersect(available) }
            if (options.all { it.isEmpty() }) null else CaptureChoice(options)
        }
        return CaptureGoal(available - selectedChoices.flatMap { it.alternatives.flatten() }.toSet(), selectedChoices)
    }

    private fun singles(ids: List<Int>) = CaptureChoice(ids.map { setOf(it) })

    private val HOENN_STARTERS = CaptureChoice(listOf(setOf(252, 253, 254), setOf(255, 256, 257), setOf(258, 259, 260)))
    private val FOSSILS = CaptureChoice(listOf(setOf(345, 346), setOf(347, 348)))
    private val KANTO_FOSSILS = CaptureChoice(listOf(setOf(138, 139), setOf(140, 141)))

    // Le partenaire et la bête associée forment un seul choix, pas deux choix indépendants.
    private val KANTO_STARTERS_AND_ROAMER = CaptureChoice(
        listOf(setOf(1, 2, 3, 244), setOf(4, 5, 6, 245), setOf(7, 8, 9, 243))
    )

    // Rubis et Émeraude n'ont qu'une Pierre Lune ; les Lunatone de Saphir en portent d'autres.
    private val MOON_STONE = singles(listOf(40, 301))

    private val RUBY = setOf(
        25, 26, 27, 28, 37, 38, 39, 40, 41, 42, 43, 44, 45, 54, 55, 63, 64, 66, 67, 72,
        73, 74, 75, 81, 82, 84, 85, 88, 89, 100, 101, 109, 110, 111, 112, 116, 117, 118, 119, 120,
        121, 127, 129, 130, 169, 170, 171, 172, 174, 177, 178, 182, 183, 184, 202, 203, 214, 218, 219, 222,
        227, 231, 232, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268,
        269, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291,
        292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312,
        313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332,
        333, 334, 335, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354,
        355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 369, 370, 371, 372, 373, 374, 375, 376,
        377, 378, 379, 381, 383, 384
    )

    private val SAPPHIRE = setOf(
        25, 26, 27, 28, 37, 38, 39, 40, 41, 42, 43, 44, 45, 54, 55, 63, 64, 66, 67, 72,
        73, 74, 75, 81, 82, 84, 85, 88, 89, 100, 101, 109, 110, 111, 112, 116, 117, 118, 119, 120,
        121, 127, 129, 130, 169, 170, 171, 172, 174, 177, 178, 182, 183, 184, 202, 203, 214, 218, 219, 222,
        227, 231, 232, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268,
        269, 270, 271, 272, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291,
        292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 304, 305, 306, 307, 308, 309, 310, 311, 312,
        313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332,
        333, 334, 336, 337, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354,
        355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 369, 370, 371, 372, 373, 374, 375, 376,
        377, 378, 379, 380, 382, 384
    )

    // Les partenaires de Johto exigent les 200 espèces de Hoenn : échanges externes nécessaires.
    private val EMERALD = setOf(
        25, 26, 27, 28, 37, 38, 39, 40, 41, 42, 43, 44, 45, 52, 53, 54, 55, 63, 64, 66,
        67, 72, 73, 74, 75, 81, 82, 84, 85, 88, 89, 100, 101, 109, 110, 111, 112, 116, 117, 118,
        119, 120, 121, 127, 129, 130, 132, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 174, 177, 178,
        179, 180, 181, 182, 183, 184, 185, 190, 191, 192, 194, 195, 202, 203, 204, 205, 207, 209, 210, 213,
        214, 216, 217, 218, 219, 222, 223, 224, 227, 228, 229, 231, 232, 234, 235, 241, 252, 253, 254, 255,
        256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275,
        276, 277, 278, 279, 280, 281, 282, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297,
        298, 299, 300, 301, 302, 303, 304, 305, 306, 309, 310, 311, 312, 313, 314, 316, 317, 318, 319, 320,
        321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 336, 338, 339, 340, 341, 342,
        343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362,
        363, 364, 365, 366, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384
    )

    private val FIRERED = setOf(
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 39, 40, 41, 42, 43, 44,
        45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64,
        66, 67, 72, 73, 74, 75, 77, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92,
        93, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113,
        114, 115, 116, 117, 118, 119, 122, 123, 124, 125, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137,
        138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 161, 162, 165, 166, 167, 168, 169,
        172, 173, 174, 175, 176, 177, 178, 182, 187, 188, 189, 193, 194, 195, 198, 201, 202, 206, 211, 214,
        218, 219, 220, 221, 225, 227, 231, 232, 236, 237, 238, 239, 242, 243, 244, 245, 246, 247, 248, 360
    )

    private val LEAFGREEN = setOf(
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        46, 47, 48, 49, 50, 51, 52, 53, 56, 57, 60, 61, 62, 63, 64, 66, 67, 69, 70, 71,
        72, 73, 74, 75, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 92, 93, 95,
        96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115,
        116, 117, 118, 119, 120, 121, 122, 124, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137,
        138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 161, 162, 165, 166, 167, 168, 169,
        172, 173, 174, 175, 176, 177, 178, 183, 184, 187, 188, 189, 193, 200, 201, 202, 206, 214, 215, 218,
        219, 220, 221, 223, 224, 226, 231, 232, 236, 237, 238, 240, 242, 243, 244, 245, 246, 247, 248, 298,
        360
    )
}
