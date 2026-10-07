package org.opensources.pokmaps.domain.map

/** Ce que devient un fossile : le Pokémon ranimé, son niveau, et le personnage qui le ranime (dans son labo). */
data class FossilUse(
    val fossilIdentifier: String,
    val fossilName: String,
    val pokemonId: Int,
    val pokemonName: String,
    val level: Int,
    val reviver: MapObject,
    val reviverMapName: String
) {
    companion object {
        /** Fossiles du jeu et ce qu'ils deviennent, par identifiant du fossile (Fossile Dôme → Kabuto…). */
        fun of(index: GameIndex, catalog: MapCatalog): Map<String, FossilUse> =
            index.offers.filter { it.kind == OfferKind.FOSSIL }.mapNotNull { offer ->
                val reviver = catalog.objectsById[offer.objectId] ?: return@mapNotNull null
                FossilUse(
                    fossilIdentifier = required(offer.itemIdentifier),
                    fossilName = required(offer.itemName),
                    pokemonId = required(offer.pokemonId),
                    pokemonName = required(offer.pokemonName),
                    level = required(offer.quantity),
                    reviver = reviver,
                    reviverMapName = catalog.maps[reviver.mapId]?.name.orEmpty()
                )
            }.associateBy { it.fossilIdentifier }

        /** La base est validée à la génération : une résurrection incomplète est une erreur. */
        private fun <T : Any> required(value: T?): T = checkNotNull(value) { "Résurrection de fossile incomplète" }
    }
}
