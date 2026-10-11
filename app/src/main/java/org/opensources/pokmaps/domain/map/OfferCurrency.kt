package org.opensources.pokmaps.domain.map

/** Monnaie d’un tarif, distincte des points de la Carte Bleue de Buena. */
enum class OfferCurrency(val identifier: String) {
    MONEY("money"),
    COINS("coins"),
    BATTLE_POINTS("battle_points"),
    ASHES("ashes");

    companion object {
        fun from(identifier: String): OfferCurrency =
            requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
                "Monnaie inconnue : $identifier"
            }
    }
}
