package org.opensources.pokmaps.data.db

/**
 * Petit monde en mémoire : carte de Kanto avec la Route 1 et Jadielle, la boutique de Jadielle et un labo. La route
 * a un dresseur, une Potion et des Roucool ; le vendeur de la boutique vend des Potions. Dans le labo, un Fossile
 * Dôme à ramasser, le scientifique qui le ranime en Kabuto, une infirmière et un comptoir des lots dont l'Abra
 * coûte plus cher dans Rouge que dans Bleu. `failing` simule une base illisible, `encountersFailing` une erreur
 * limitée à la lecture des rencontres.
 */
internal class FakeMapDao(
    private val failing: Boolean = false,
    private val encountersFailing: Boolean = false,
    private val includeHiddenItem: Boolean = false
) : MapDao {
    override suspend fun maps(versionGroupId: Int) = read {
        listOf(
            MapEntity(WORLD, versionGroupId, "kanto", "Kanto", null, 0, 0, 480, 432, 2),
            MapEntity(ROUTE_1, versionGroupId, "route-1", "Route 1", WORLD, 160, 0, 160, 288, 0),
            MapEntity(VIRIDIAN, versionGroupId, "viridian-city", "Jadielle", WORLD, 160, 288, 160, 144, 0),
            MapEntity(MART, versionGroupId, "viridian-mart", "Boutique de Jadielle", null, 0, 0, 128, 128, 1),
            MapEntity(LAB, versionGroupId, "pokemon-lab", "Labo Pokémon", null, 0, 0, 128, 128, 1)
        )
    }

    override suspend fun warps(versionGroupId: Int) = read {
        listOf(
            MapWarpEntity(1, VIRIDIAN, 200, 330, MART, 64, 112),
            MapWarpEntity(2, MART, 64, 120, VIRIDIAN, 200, 338)
        )
    }

    override suspend fun objects(versionGroupId: Int) = read {
        listOf(
            mapObject(TRAINER, ROUTE_1, 200 to 100, "trainer", "Gamin", "youngster", trainerClass = "youngster"),
            mapObject(CLERK, MART, 40 to 40, "npc", "Vendeur", "clerk"),
            mapObject(ITEM, ROUTE_1, 220 to 120, "item", "Potion", item = POTION),
            *hiddenItems(),
            mapObject(FOSSIL, LAB, 24 to 24, "npc_object", "Fossile", "fossil"),
            mapObject(REVIVER, LAB, 56 to 24, "npc", "Scientifique", "scientist"),
            mapObject(NURSE, LAB, 88 to 24, "npc", "Infirmière", "nurse"),
            mapObject(PRIZES, LAB, 56 to 88, "prize_vendor", "Comptoir des lots")
        )
    }

    private fun hiddenItems(): Array<MapObjectRow> = if (includeHiddenItem) {
        arrayOf(mapObject(HIDDEN_ITEM, ROUTE_1, 240 to 120, "hidden_item", "Super Potion", item = POTION))
    } else {
        emptyArray()
    }

    private fun mapObject(
        id: Int,
        mapId: Int,
        position: Pair<Int, Int>,
        kind: String,
        name: String,
        sprite: String? = null,
        item: Int? = null,
        trainerClass: String? = null
    ) = MapObjectRow(
        id = id,
        mapId = mapId,
        kind = kind,
        x = position.first,
        y = position.second,
        sprite = sprite,
        itemId = item,
        itemIdentifier = item?.let { "potion" },
        itemName = item?.let { "Potion" },
        pokemonId = null,
        pokemonName = null,
        level = null,
        trainerClass = trainerClass,
        name = name
    )

    override suspend fun areas(versionGroupId: Int) = read { listOf(MapAreaRow(ROUTE_1, AREA, "Route 1")) }

    override suspend fun encounters(versionId: Int, areaIds: List<Int>) = read {
        check(!encountersFailing) { FakeGameDao.BROKEN }
        if (AREA in areaIds) listOf(PIDGEY_ENCOUNTER) else emptyList()
    }

    override suspend fun pokemonAreaMethods(versionId: Int, pokemonId: Int) =
        read { if (pokemonId == PIDGEY) listOf(AreaMethodRow(AREA, "walk")) else emptyList() }

    override suspend fun pokemonGivers(versionId: Int, pokemonId: Int) = read {
        when (pokemonId) {
            KABUTO -> listOf(REVIVER)
            ABRA -> listOf(PRIZES)
            else -> emptyList()
        }
    }

    override suspend fun items(versionGroupId: Int) = read {
        listOf(
            ItemRow(POTION, "potion", "Potion", true, "healing", null),
            ItemRow(DOME_FOSSIL, "dome-fossil", "Fossile Dôme", true, "dex-completion", null)
        )
    }

    override suspend fun offerLinks(versionId: Int) = read {
        listOf(
            OfferLinkRow(CLERK, "sale", "potion", "Potion", null, null, null, 300, null, null, null),
            OfferLinkRow(FOSSIL, "gift_item", "dome-fossil", "Fossile Dôme", null, null, null, null, 1, null, null),
            OfferLinkRow(
                REVIVER, "fossil", "dome-fossil", "Fossile Dôme", KABUTO, "Kabuto", null, null, 30, null, null
            ),
            OfferLinkRow(NURSE, "heal", null, null, null, null, null, null, null, null, null),
            OfferLinkRow(
                PRIZES, "prize_pokemon", null, null, ABRA, "Abra", null, abraCoins(versionId), 9, null, null
            )
        )
    }

    override suspend fun itemEvolutions(versionGroupId: Int, itemId: Int) = read { emptyList<ItemEvolutionRow>() }

    override suspend fun spots(versionGroupId: Int) = read { listOf(MapSpotEntity(1, ROUTE_1, "grass", 200, 60)) }

    override suspend fun trainerParty(objectId: Int) =
        read { if (objectId == TRAINER) listOf(TrainerPokemonRow(1, 19, "Rattata", 5)) else emptyList() }

    override suspend fun trainerMoves(objectId: Int, versionGroupId: Int) = read { emptyList<TrainerMoveRow>() }

    override suspend fun offers(objectId: Int, versionId: Int) = read {
        when (objectId) {
            CLERK -> listOf(offer("sale", POTION, "potion", "Potion", price = 300))

            FOSSIL -> listOf(offer("gift_item", DOME_FOSSIL, "dome-fossil", "Fossile Dôme", quantity = 1))

            REVIVER -> listOf(offer("fossil", DOME_FOSSIL, "dome-fossil", "Fossile Dôme", KABUTO, "Kabuto", 30))

            NURSE -> listOf(offer("heal"))

            PRIZES -> listOf(
                offer("prize_pokemon", pokemon = ABRA, pokemonName = "Abra", quantity = 9, price = abraCoins(versionId))
            )

            else -> emptyList()
        }
    }

    private fun offer(
        kind: String,
        item: Int? = null,
        itemIdentifier: String? = null,
        itemName: String? = null,
        pokemon: Int? = null,
        pokemonName: String? = null,
        quantity: Int? = null,
        price: Int? = null
    ) = NpcOfferRow(
        kind = kind,
        itemId = item,
        itemIdentifier = itemIdentifier,
        itemName = itemName,
        itemHasSprite = item?.let { true },
        pokemonId = pokemon,
        pokemonName = pokemonName,
        quantity = quantity,
        price = price,
        wantedPokemonId = null,
        wantedPokemonName = null,
        wantedItemId = null,
        wantedItemIdentifier = null,
        wantedItemName = null,
        wantedItemHasSprite = null
    )

    /** Les lots du Casino diffèrent entre Rouge (version 1) et Bleu. */
    private fun abraCoins(versionId: Int) = if (versionId == 1) RED_ABRA_COINS else BLUE_ABRA_COINS

    override suspend fun item(itemId: Int, versionGroupId: Int) = read {
        if (itemId == POTION) {
            ItemDetailsRow(
                POTION, "potion", "Potion", true, "Soigne 20 PV.", null, null, null, null, null, null, null, null
            )
        } else {
            null
        }
    }

    private fun <T> read(rows: () -> T): T = if (failing) throw IllegalStateException(FakeGameDao.BROKEN) else rows()

    companion object {
        const val WORLD = 1000
        const val ROUTE_1 = 1001
        const val VIRIDIAN = 1002
        const val MART = 1003
        const val LAB = 1004
        const val TRAINER = 10
        const val CLERK = 11
        const val ITEM = 12
        const val HIDDEN_ITEM = 18
        const val FOSSIL = 13
        const val REVIVER = 14
        const val NURSE = 15
        const val PRIZES = 16
        const val POTION = 17
        const val DOME_FOSSIL = 102
        const val AREA = 100
        const val PIDGEY = 16
        const val ABRA = 63
        const val KABUTO = 140
        const val RED_ABRA_COINS = 180
        const val BLUE_ABRA_COINS = 120

        private val PIDGEY_ENCOUNTER = EncounterRow(
            versionId = 1,
            versionName = "Rouge",
            areaId = AREA,
            areaName = "Route 1",
            pokemonId = PIDGEY,
            pokemonName = "Roucool",
            method = "walk",
            methodName = "Marche",
            methodOrder = 1,
            isOneOff = false,
            minLevel = 2,
            maxLevel = 5,
            chance = 50.0,
            quantity = 1,
            note = null,
            conditions = null
        )
    }
}
