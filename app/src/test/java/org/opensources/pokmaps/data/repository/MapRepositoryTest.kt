package org.opensources.pokmaps.data.repository

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferItem

class MapRepositoryTest {
    @Test
    fun catalogKeepsTheObjectsOfEachVersion() = runTest {
        val repository = MapRepository(FakeMapDao(includeVersionPokemon = true))

        fun level(catalog: MapCatalog): Int? =
            catalog.objects.getValue(FakeMapDao.ROUTE_1).single { it.pokemonId == FakeMapDao.SNORLAX }.level

        // Rouge et Bleu partagent leurs cartes, mais pas ce Pokémon fixe : chaque version a son catalogue.
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.RED)))
        assertEquals(FakeMapDao.BLUE_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.BLUE)))
    }

    @Test
    fun secondGenerationOffersKeepHeldItemsTreesAndServices() = runTest {
        val repository = MapRepository(FakeMapDao())
        val berry = OfferItem(FakeMapDao.BERRY, "oran-berry", "Baie Oran", hasSprite = true)

        val offers = repository.offers(FakeGameDao.RED, FakeMapDao.SECOND_GENERATION)

        assertEquals(
            listOf(
                NpcOffer.GiftPokemon(FakeMapDao.CYNDAQUIL, "Héricendre", 5, heldItem = berry),
                NpcOffer.GiftPokemon(FakeMapDao.PIDGEY, "Roucool", 10, heldItem = null),
                NpcOffer.GiftEgg(FakeMapDao.TOGEPI, "Togepi", 5),
                NpcOffer.Trade(FakeMapDao.ABRA, "Abra", FakeMapDao.PIDGEY, "Roucool", heldItem = berry),
                NpcOffer.FruitTree(berry),
                NpcOffer.Service(CharacterService.GROOMING, price = 500),
                NpcOffer.Service(CharacterService.MOVE_DELETER),
                NpcOffer.Service(CharacterService.MOVE_TUTOR, price = 4000),
                NpcOffer.PointPrize(berry, points = 2)
            ),
            offers
        )
    }
}
