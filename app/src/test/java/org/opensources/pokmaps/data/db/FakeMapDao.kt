package org.opensources.pokmaps.data.db

/**
 * Petit monde en mémoire : carte de Kanto avec la Route 1 et Jadielle, la boutique de Jadielle et un labo. La route
 * a un dresseur, une Potion et des Roucool ; le vendeur de la boutique vend des Potions. Dans le labo, un Fossile
 * Dôme à ramasser, le scientifique qui le ranime en Kabuto, une infirmière et un comptoir des lots dont l'Abra
 * coûte plus cher dans Rouge que dans Bleu. `failing` simule une base illisible, `encountersFailing` une erreur
 * limitée à la lecture des rencontres. `includeVersionPokemon` ajoute sur la Route 1 un Pokémon fixe dont le niveau
 * dépend de la version, comme la requête qui ne garde que les objets de la version demandée. Un personnage d'un
 * jour de la semaine (`SIBLING`) donne une baie le lundi soir, après deux étapes du scénario.
 */
internal class FakeMapDao(
    private val failing: Boolean = false,
    private val encountersFailing: Boolean = false,
    private val includeHiddenItem: Boolean = false,
    private val includeVersionPokemon: Boolean = false,
    private val timedEncounters: Boolean = false,
    private val emptyMaps: Boolean = false
) : MapDao {
    override suspend fun maps(versionGroupId: Int) = read {
        if (emptyMaps) return@read emptyList()
        listOf(
            MapEntity(WORLD, versionGroupId, "kanto", "Kanto", null, 0, 0, 480, 432, 2, isWorld = true),
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

    override suspend fun objects(versionGroupId: Int, versionId: Int) = read {
        listOf(
            mapObject(TRAINER, ROUTE_1, 200 to 100, "trainer", "Gamin", "youngster", trainerClass = "youngster"),
            mapObject(CLERK, MART, 40 to 40, "npc", "Vendeur", "clerk"),
            mapObject(ITEM, ROUTE_1, 220 to 120, "item", "Potion", item = POTION),
            *hiddenItems(),
            mapObject(FOSSIL, LAB, 24 to 24, "npc_object", "Fossile", "fossil"),
            mapObject(REVIVER, LAB, 56 to 24, "npc", "Scientifique", "scientist"),
            mapObject(NURSE, LAB, 88 to 24, "npc", "Infirmière", "nurse"),
            mapObject(PRIZES, LAB, 56 to 88, "prize_vendor", "Comptoir des lots"),
            *versionPokemon(versionId)
        )
    }

    private fun versionPokemon(versionId: Int): Array<MapObjectRow> = if (includeVersionPokemon) {
        val level = if (versionId == FakeGameDao.RED.versionId) RED_SNORLAX_LEVEL else BLUE_SNORLAX_LEVEL
        arrayOf(
            mapObject(SNORLAX_OBJECT, ROUTE_1, 280 to 120, "pokemon", "Ronflex")
                .copy(pokemonId = SNORLAX, pokemonName = "Ronflex", level = level)
        )
    } else {
        emptyArray()
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
        if (AREA !in areaIds) return@read emptyList()
        if (timedEncounters) {
            listOf(
                PIDGEY_ENCOUNTER.copy(conditions = "La journée", conditionIdentifiers = "time-day"),
                PIDGEY_ENCOUNTER.copy(
                    pokemonId = 163,
                    pokemonName = "Hoothoot",
                    conditions = "La nuit",
                    conditionIdentifiers = "time-night"
                )
            )
        } else {
            listOf(PIDGEY_ENCOUNTER)
        }
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

    override suspend fun items(versionGroupId: Int, versionId: Int) = read {
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

            SECOND_GENERATION -> secondGenerationOffers()

            SIBLING -> listOf(
                offer(
                    "gift_item",
                    BERRY,
                    "oran-berry",
                    "Baie Oran",
                    quantity = 1,
                    id = SIBLING_GIFT,
                    timeMask = 4,
                    weekdayMask = 2
                ),
                offer("gift_item", POTION, "potion", "Potion", quantity = 1, id = SIBLING_POTION)
            )

            PRIZES -> listOf(
                offer("prize_pokemon", pokemon = ABRA, pokemonName = "Abra", quantity = 9, price = abraCoins(versionId))
            )

            else -> emptyList()
        }
    }

    override suspend fun offerStories(objectId: Int) = read {
        if (objectId == SIBLING) {
            listOf(
                OfferStoryRow(SIBLING_GIFT, "Après le badge Zéphyr"),
                OfferStoryRow(SIBLING_GIFT, "Après la libération de la Tour Radio")
            )
        } else {
            emptyList()
        }
    }

    /** Offres propres à la 2e génération : objet tenu, œuf, arbre à baies et services. */
    private fun secondGenerationOffers() = listOf(
        offer("gift_pokemon", BERRY, "oran-berry", "Baie Oran", CYNDAQUIL, "Héricendre", 5),
        offer("gift_pokemon", pokemon = PIDGEY, pokemonName = "Roucool", quantity = 10),
        offer("gift_egg", pokemon = TOGEPI, pokemonName = "Togepi", quantity = 5),
        offer("trade", BERRY, "oran-berry", "Baie Oran", ABRA, "Abra", wanted = PIDGEY to "Roucool"),
        offer("fruit_tree", BERRY, "oran-berry", "Baie Oran"),
        offer("grooming", price = 500),
        offer("move_deleter"),
        offer("move_tutor", price = 4000),
        offer("point_prize", BERRY, "oran-berry", "Baie Oran", price = 2)
    )

    private fun offer(
        kind: String,
        item: Int? = null,
        itemIdentifier: String? = null,
        itemName: String? = null,
        pokemon: Int? = null,
        pokemonName: String? = null,
        quantity: Int? = null,
        price: Int? = null,
        wanted: Pair<Int, String>? = null,
        id: Int = 0,
        timeMask: Int? = null,
        weekdayMask: Int? = null
    ) = NpcOfferRow(
        id = id,
        kind = kind,
        itemId = item,
        itemIdentifier = itemIdentifier,
        itemName = itemName,
        itemHasSprite = item?.let { true },
        pokemonId = pokemon,
        pokemonName = pokemonName,
        quantity = quantity,
        price = price,
        wantedPokemonId = wanted?.first,
        wantedPokemonName = wanted?.second,
        wantedItemId = null,
        wantedItemIdentifier = null,
        wantedItemName = null,
        wantedItemHasSprite = null,
        timeMask = timeMask,
        weekdayMask = weekdayMask
    )

    /** Les lots du Casino diffèrent entre Rouge (version 1) et Bleu. */
    private fun abraCoins(versionId: Int) = if (versionId == 1) RED_ABRA_COINS else BLUE_ABRA_COINS

    override suspend fun item(itemId: Int, versionGroupId: Int) = read {
        if (itemId == POTION) {
            ItemDetailsRow(
                POTION, "potion", "Potion", true, "Soigne 20 PV.", null, null, null, null, null, null, null, null,
                null, null, null
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
        const val SNORLAX_OBJECT = 19
        const val SNORLAX = 143
        const val RED_SNORLAX_LEVEL = 30
        const val BLUE_SNORLAX_LEVEL = 50
        const val SECOND_GENERATION = 20
        const val BERRY = 132
        const val CYNDAQUIL = 155
        const val TOGEPI = 175

        /** Personnage d'un jour de la semaine : une baie le lundi soir après deux étapes, une Potion toujours. */
        const val SIBLING = 21
        const val SIBLING_GIFT = 1
        const val SIBLING_POTION = 2

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
