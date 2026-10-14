package org.opensources.pokmaps.data.repository

import kotlin.coroutines.ContinuationInterceptor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.TrainerMoveRow
import org.opensources.pokmaps.data.db.TrainerPokemonRow
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCondition
import org.opensources.pokmaps.domain.map.OfferCurrency
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.TeamVariant
import org.opensources.pokmaps.domain.map.TeamVariantKind
import org.opensources.pokmaps.domain.map.Weekday
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.usecase.ObserveItemPageUseCase

class MapRepositoryTest {
    @Test
    fun rivalTeamsAreGroupedByVariantWithTheirOwnMoves() = runTest {
        fun mon(team: Int, variant: Int, variantName: String, pokemon: Int, name: String) =
            TrainerPokemonRow(team, "player-starter", variant, variantName, 1, pokemon, name, 5)
        val tackle = TrainerMoveRow(2, 1, 1, 33, "Charge", 35, 100, 35, "physical", 1, "normal", "Normal")
        val dao = object : MapDao by FakeMapDao() {
            override suspend fun trainerParty(objectId: Int) =
                listOf(mon(1, 4, "Salamèche", 7, "Carapuce"), mon(2, 7, "Carapuce", 1, "Bulbizarre"))
            override suspend fun trainerMoves(objectId: Int, versionGroupId: Int) = listOf(tackle)
        }
        val teams = MapRepository(dao, Dispatchers.Unconfined).trainerTeams(FakeGameDao.RED, FakeMapDao.TRAINER)
        assertEquals(
            listOf(
                TeamVariant(TeamVariantKind.PLAYER_STARTER, 4, "Salamèche"),
                TeamVariant(TeamVariantKind.PLAYER_STARTER, 7, "Carapuce")
            ),
            teams.map { it.variant }
        )
        val moves = teams.map { team -> team.members.single().moves.map { it.name } }
        assertEquals(listOf(emptyList(), listOf("Charge")), moves)
    }

    @Test
    fun hoennSalesKeepTheirCurrencyAndTutorsCanBeFree() = runTest {
        val delegate = FakeMapDao()
        val sale = delegate.offers(FakeMapDao.CLERK, FakeGameDao.RED.versionId).single()
        val freeTutor = sale.copy(
            kind = "move_tutor",
            itemId = null,
            itemIdentifier = null,
            itemName = null,
            itemHasSprite = null,
            price = null
        )
        val rows = listOf(sale.copy(currency = "battle_points"), sale.copy(currency = "ashes"), freeTutor)
        val link = delegate.offerLinks(FakeGameDao.RED.versionId).first { it.kind == "sale" }
        val dao = object : MapDao by delegate {
            override suspend fun offers(objectId: Int, versionId: Int) = rows
            override suspend fun offerLinks(versionId: Int) = listOf(link.copy(currency = "ashes"))
        }
        val repository = MapRepository(dao, Dispatchers.Unconfined)
        val offers = repository.offers(FakeGameDao.RED, FakeMapDao.CLERK)
        assertEquals(OfferCurrency.ASHES, repository.index(FakeGameDao.RED).offers.single().currency)
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        val page = checkNotNull(
            ObserveItemPageUseCase(games, repository, HoennRepository { error("Hors Hoenn") })("potion").first()
        )
        assertEquals(OfferCurrency.ASHES, page.sold.single().currency)
        val item = OfferItem(FakeMapDao.POTION, "potion", "Potion", true)
        assertEquals(
            listOf(
                NpcOffer.Sale(item, 300, currency = OfferCurrency.BATTLE_POINTS),
                NpcOffer.Sale(item, 300, currency = OfferCurrency.ASHES),
                NpcOffer.Service(CharacterService.MOVE_TUTOR)
            ),
            offers
        )
    }

    @Test
    fun fruitTreesUseTheirOwnLayerAndMatchingItemSprite() = runTest {
        val repository = MapRepository(FakeMapDao(includeFruitTree = true), Dispatchers.Unconfined)
        val catalog = repository.catalog(FakeGameDao.GOLD)
        val tree = catalog.objects.getValue(FakeMapDao.ROUTE_1).single { it.id == FakeMapDao.SECOND_GENERATION }
        assertEquals(OfferItem(FakeMapDao.BERRY, "oran-berry", "Baie Oran", true), tree.fruit)
        assertEquals(
            org.opensources.pokmaps.domain.map.MapLayer.FRUIT_TREES,
            org.opensources.pokmaps.domain.map.MapLayer.of(tree)
        )
        assertEquals(
            org.opensources.pokmaps.domain.map.Footprint.ITEM,
            org.opensources.pokmaps.domain.map.MarkerSizing.footprintOf(tree)
        )
        assertEquals(264, tree.x)
        assertEquals(136, tree.y)
    }

    @Test
    fun catalogKeepsTheObjectsOfEachVersion() = runTest {
        val repository = MapRepository(FakeMapDao(includeVersionPokemon = true), Dispatchers.Unconfined)

        fun level(catalog: MapCatalog): Int? =
            catalog.objects.getValue(FakeMapDao.ROUTE_1).single { it.pokemonId == FakeMapDao.SNORLAX }.level

        // Rouge et Bleu partagent leurs cartes, mais pas ce Pokémon fixe : chaque version a son catalogue.
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.RED)))
        assertEquals(FakeMapDao.BLUE_SNORLAX_LEVEL, level(repository.catalog(FakeGameDao.BLUE)))
    }

    @Test
    fun eachVersionReadsItsOwnMapsObjectsAndOffers() = runTest {
        val repository =
            MapRepository(FakeMapDao(includeVersionPokemon = true, includeBlueHideout = true), Dispatchers.Unconfined)

        val red = repository.catalog(FakeGameDao.RED)
        val blue = repository.catalog(FakeGameDao.BLUE)

        // La planque n'existe que dans Bleu : Rouge ne la lit pas, ni le passage qui y mène.
        assertFalse(FakeMapDao.BLUE_HIDEOUT in red.maps)
        assertTrue(red.warps.values.flatten().none { it.targetMapId == FakeMapDao.BLUE_HIDEOUT })
        assertTrue(FakeMapDao.BLUE_HIDEOUT in blue.maps)
        assertEquals(1, blue.warps.values.flatten().count { it.targetMapId == FakeMapDao.BLUE_HIDEOUT })
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, snorlaxLevel(red))
        assertEquals(FakeMapDao.BLUE_SNORLAX_LEVEL, snorlaxLevel(blue))
        assertEquals(FakeMapDao.RED_ABRA_COINS, abraPrice(repository, FakeGameDao.RED))
        assertEquals(FakeMapDao.BLUE_ABRA_COINS, abraPrice(repository, FakeGameDao.BLUE))
    }

    @Test
    fun onlyTheTwoLastVersionsStayInMemoryAndAForgottenOneIsReadAgain() = runTest {
        val repository = MapRepository(FakeMapDao(includeVersionPokemon = true), Dispatchers.Unconfined)
        val red = repository.catalog(FakeGameDao.RED)
        val redIndex = repository.index(FakeGameDao.RED)
        val gold = repository.catalog(FakeGameDao.GOLD)
        repository.index(FakeGameDao.GOLD)

        // Rouge, consulté de nouveau, devient plus récent qu'Or : c'est Or qu'oublie l'arrivée de Rubis.
        assertSame(red, repository.catalog(FakeGameDao.RED))
        assertSame(redIndex, repository.index(FakeGameDao.RED))
        repository.catalog(FakeGameDao.RUBY)
        repository.index(FakeGameDao.RUBY)
        assertSame(red, repository.catalog(FakeGameDao.RED))
        assertSame(redIndex, repository.index(FakeGameDao.RED))
        assertNotSame(gold, repository.catalog(FakeGameDao.GOLD))
        repository.index(FakeGameDao.GOLD)

        // Rouge est oublié à son tour ; relu ensuite, il retrouve les mêmes cartes que Bleu et ses propres objets.
        val blue = repository.catalog(FakeGameDao.BLUE)
        repository.index(FakeGameDao.BLUE)
        val reloaded = repository.catalog(FakeGameDao.RED)
        assertNotSame(red, reloaded)
        assertNotSame(redIndex, repository.index(FakeGameDao.RED))
        assertEquals(red, reloaded)
        assertEquals(blue.maps, reloaded.maps)
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, snorlaxLevel(reloaded))
        assertEquals(FakeMapDao.RED_ABRA_COINS, abraPrice(repository, FakeGameDao.RED))
    }

    @Test
    fun concurrentRequestsReadEachVersionOnceAndNeverMixThem() = runTest {
        val repository = MapRepository(FakeMapDao(includeVersionPokemon = true), StandardTestDispatcher(testScheduler))

        val requests = listOf(FakeGameDao.RED, FakeGameDao.BLUE, FakeGameDao.RED, FakeGameDao.BLUE).map { game ->
            async { game to repository.catalog(game) }
        }
        val indexes = listOf(FakeGameDao.BLUE, FakeGameDao.RED).map { game -> async { repository.index(game) } }
        val (red, blue, redAgain, blueAgain) = requests.awaitAll()

        assertSame(red.second, redAgain.second)
        assertSame(blue.second, blueAgain.second)
        assertEquals(FakeMapDao.RED_SNORLAX_LEVEL, snorlaxLevel(red.second))
        assertEquals(FakeMapDao.BLUE_SNORLAX_LEVEL, snorlaxLevel(blue.second))
        val (blueIndex, redIndex) = indexes.awaitAll()
        assertEquals(FakeMapDao.BLUE_ABRA_COINS, blueIndex.offers.single { it.pokemonId == FakeMapDao.ABRA }.price)
        assertEquals(FakeMapDao.RED_ABRA_COINS, redIndex.offers.single { it.pokemonId == FakeMapDao.ABRA }.price)
    }

    private fun snorlaxLevel(catalog: MapCatalog): Int? =
        catalog.objects.getValue(FakeMapDao.ROUTE_1).single { it.pokemonId == FakeMapDao.SNORLAX }.level

    private suspend fun abraPrice(repository: MapRepository, game: Game): Int? =
        repository.index(game).offers.single { it.pokemonId == FakeMapDao.ABRA }.price

    @Test
    fun secondGenerationOffersKeepHeldItemsTreesAndServices() = runTest {
        val repository = MapRepository(FakeMapDao(), Dispatchers.Unconfined)
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

    @Test
    fun offersCarryTheirTimesDaysAndStorySteps() = runTest {
        val repository = MapRepository(FakeMapDao(), Dispatchers.Unconfined)

        val (berry, potion) = repository.offers(FakeGameDao.RED, FakeMapDao.SIBLING)

        assertEquals(
            OfferCondition(
                times = setOf(EncounterTime.NIGHT),
                weekdays = setOf(Weekday.MONDAY),
                story = listOf("Après le badge Zéphyr", "Après la libération de la Tour Radio")
            ),
            berry.condition
        )
        assertEquals(OfferCondition.ALWAYS, potion.condition)
    }

    @Test
    fun catalogAndIndexAreBuiltOnTheComputationDispatcher() = runTest {
        val computation = StandardTestDispatcher(testScheduler)
        val readOn = mutableListOf<ContinuationInterceptor?>()
        val delegate = FakeMapDao()
        val dao = object : MapDao by delegate {
            override suspend fun maps(versionGroupId: Int, versionId: Int) = delegate.maps(versionGroupId, versionId)
                .also { readOn += currentCoroutineContext()[ContinuationInterceptor] }

            override suspend fun items(versionGroupId: Int, versionId: Int) = delegate.items(versionGroupId, versionId)
                .also { readOn += currentCoroutineContext()[ContinuationInterceptor] }
        }
        val repository = MapRepository(dao, computation)

        repository.catalog(FakeGameDao.RED)
        repository.index(FakeGameDao.RED)

        // Lectures et conversions qui les suivent : jamais sur le contexte de l'appelant (le fil principal).
        assertTrue(readOn.size >= 2)
        assertTrue(readOn.all { it === computation })
    }

    @Test(expected = IllegalStateException::class)
    fun unreadableOffersAreAnError() = runTest {
        MapRepository(FakeMapDao(failing = true), Dispatchers.Unconfined).offers(FakeGameDao.RED, FakeMapDao.SIBLING)
    }
}
