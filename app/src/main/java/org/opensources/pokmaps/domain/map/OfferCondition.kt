package org.opensources.pokmaps.domain.map

import org.opensources.pokmaps.domain.model.EncounterTime

/** Jour de la semaine du jeu (2e génération), avec son bit dans npc_offer.weekday_mask (dimanche : bit 0). */
enum class Weekday(val bit: Int) {
    MONDAY(1),
    TUESDAY(2),
    WEDNESDAY(3),
    THURSDAY(4),
    FRIDAY(5),
    SATURDAY(6),
    SUNDAY(0)
}

/**
 * Ce qu'exige une offre pour être possible : moments de la journée, jours de la semaine et étapes du scénario, lus
 * sur tous les chemins du script qui y mènent (conditions nécessaires). Un ensemble vide ne restreint rien.
 */
data class OfferCondition(
    val times: Set<EncounterTime> = emptySet(),
    val weekdays: Set<Weekday> = emptySet(),
    val story: List<String> = emptyList()
) {
    /** Vrai si l'offre est possible à tout moment, tous les jours et sans étape préalable. */
    val isAlways: Boolean get() = times.isEmpty() && weekdays.isEmpty() && story.isEmpty()

    companion object {
        val ALWAYS = OfferCondition()

        // Bits de npc_offer.time_mask, dans l'ordre des moments de pret (matin, jour, nuit).
        private val TIME_BITS = listOf(EncounterTime.MORNING, EncounterTime.DAY, EncounterTime.NIGHT)
        private val ALL_TIMES = (1 shl TIME_BITS.size) - 1
        private val ALL_WEEKDAYS = (1 shl Weekday.entries.size) - 1

        /**
         * Condition lue dans la base : `null` ne restreint rien ; un masque vide ou complet est refusé, la génération
         * écrivant `null` à sa place (tools/pokemaps_data/builder_maps.py).
         */
        fun fromMasks(timeMask: Int?, weekdayMask: Int?, story: List<String>): OfferCondition {
            require(timeMask == null || timeMask in 1 until ALL_TIMES) { "Masque des moments invalide : $timeMask" }
            require(weekdayMask == null || weekdayMask in 1 until ALL_WEEKDAYS) {
                "Masque des jours invalide : $weekdayMask"
            }
            require(story.none { it.isBlank() }) { "Étape du scénario vide" }
            val times = timeMask?.let { mask -> TIME_BITS.filterIndexed { bit, _ -> (mask and (1 shl bit)) != 0 } }
            val weekdays = weekdayMask?.let { mask -> Weekday.entries.filter { (mask and (1 shl it.bit)) != 0 } }
            return OfferCondition(times.orEmpty().toSet(), weekdays.orEmpty().toSet(), story)
        }
    }
}

/**
 * Condition commune à toutes les offres, si elle restreint quelque chose : elle se lit une fois pour le personnage
 * (la Boutique de Jadielle n'ouvre qu'après le colis) au lieu d'être répétée sous chaque offre. `null` sinon.
 */
fun List<NpcOffer>.sharedCondition(): OfferCondition? =
    map { it.condition }.distinct().singleOrNull()?.takeUnless { it.isAlways }
