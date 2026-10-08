package org.opensources.pokmaps.domain.map

/** Niveau d'une carte intérieure dans son bâtiment ou sa grotte, d'après le suffixe de son identifiant. */
sealed interface FloorLevel {
    /** Rang de haut en bas : le toit en haut, l'ascenseur à part, tout en bas. */
    val order: Int

    /** Étage hors sol : 0 pour le rez-de-chaussée (« 1f »), 1 pour le 1er étage (« 2f »)… */
    data class Storey(val number: Int) : FloorLevel {
        override val order: Int get() = number
    }

    /** Sous-sol : 1 pour le 1er sous-sol (« b1f »)… */
    data class Basement(val number: Int) : FloorLevel {
        override val order: Int get() = -number
    }

    data object Roof : FloorLevel {
        override val order: Int get() = ROOF_ORDER
    }

    data object Elevator : FloorLevel {
        override val order: Int get() = ELEVATOR_ORDER
    }

    companion object {
        /** Bâtiment et niveau d'une carte (« mt-moon-b2f » → « mt-moon », 2e sous-sol), null sans niveau. */
        fun parse(identifier: String): Pair<String, FloorLevel>? {
            val floor = identifier.removeSuffix("-plan")
            NUMBERED.matchEntire(floor)?.let { match ->
                val (building, basement, number) = match.destructured
                val n = number.toInt()
                return building to if (basement.isEmpty()) Storey(n - 1) else Basement(n)
            }
            return when {
                floor.endsWith(ROOF) -> floor.removeSuffix(ROOF) to Roof
                floor.endsWith(ELEVATOR) -> floor.removeSuffix(ELEVATOR) to Elevator
                else -> null
            }
        }
    }
}

private val NUMBERED = Regex("^(.+)-(b?)(\\d+)f$")
private const val ROOF = "-roof"
private const val ELEVATOR = "-elevator"
private const val ROOF_ORDER = 1_000
private const val ELEVATOR_ORDER = -1_000

/** Étage d'un bâtiment ou d'une grotte à plusieurs niveaux (carte intérieure affichable). */
data class MapFloor(val mapId: Int, val level: FloorLevel, val name: String = "")
