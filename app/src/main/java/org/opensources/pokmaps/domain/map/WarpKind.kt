package org.opensources.pokmaps.domain.map

/** Nature d'un passage : un warp du jeu, ou un passage que le moteur réalise autrement. */
enum class WarpKind(val identifier: String?) {
    /** Porte, escalier ou entrée de grotte. */
    WARP(null),

    /** Plongée ou remontée dont le script fixe la destination (Épave, Sanctuaire, Atalanopolis). */
    DIVE("dive"),

    /** Trajet en téléphérique entre la Route 112 et le Mont Chimnée. */
    CABLE_CAR("cable_car"),

    /** Apparition de l'Île Mirage sur sa route, puis retour à la route sans l'île. */
    MIRAGE("mirage"),

    /** Entrée d'une Base Secrète, vers la carte modèle de son type. */
    SECRET_BASE("secret_base");

    companion object {
        fun from(identifier: String?): WarpKind =
            requireNotNull(entries.firstOrNull { it.identifier == identifier }) { "Passage inconnu : $identifier" }
    }
}
