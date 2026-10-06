package org.opensources.pokmaps.data.db

/**
 * Petit monde en mémoire : carte de Kanto avec la Route 1 et Jadielle, et la boutique de Jadielle. La route a un
 * dresseur, une Potion et des Roucool ; le vendeur de la boutique vend des Potions. `failing` simule une base
 * illisible, `encountersFailing` une erreur limitée à la lecture des rencontres.
 */
internal class FakeMapDao(private val failing: Boolean = false, private val encountersFailing: Boolean = false) :
    MapDao {
    override suspend fun maps(versionGroupId: Int) = read {
        listOf(
            MapEntity(WORLD, versionGroupId, "kanto", "Kanto", null, 0, 0, 480, 432, 2),
            MapEntity(ROUTE_1, versionGroupId, "route-1", "Route 1", WORLD, 160, 0, 160, 288, 0),
            MapEntity(VIRIDIAN, versionGroupId, "viridian-city", "Jadielle", WORLD, 160, 288, 160, 144, 0),
            MapEntity(MART, versionGroupId, "viridian-mart", "Boutique de Jadielle", null, 0, 0, 128, 128, 1)
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
            mapObject(
                TRAINER,
                ROUTE_1,
                200 to 100,
                "trainer",
                "Gamin",
                sprite = "youngster",
                trainerClass = "youngster"
            ),
            mapObject(CLERK, MART, 40 to 40, "npc", "Vendeur", sprite = "clerk"),
            mapObject(ITEM, ROUTE_1, 220 to 120, "item", "Potion", item = POTION)
        )
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

    override suspend fun pokemonGivers(versionGroupId: Int, pokemonId: Int) = read { emptyList<Int>() }

    override suspend fun items(versionGroupId: Int) =
        read { listOf(ItemRow(POTION, "potion", "Potion", true, "healing", null)) }

    override suspend fun offerLinks(versionGroupId: Int) = read {
        listOf(OfferLinkRow(CLERK, "sale", "potion", "Potion", null, null, null, 300, null))
    }

    override suspend fun itemEvolutions(versionGroupId: Int, itemId: Int) = read { emptyList<ItemEvolutionRow>() }

    override suspend fun spots(versionGroupId: Int) = read { listOf(MapSpotEntity(1, ROUTE_1, "grass", 200, 60)) }

    override suspend fun trainerParty(objectId: Int) =
        read { if (objectId == TRAINER) listOf(TrainerPokemonRow(1, 19, "Rattata", 5)) else emptyList() }

    override suspend fun trainerMoves(objectId: Int, versionGroupId: Int) = read { emptyList<TrainerMoveRow>() }

    override suspend fun offers(objectId: Int) = read {
        if (objectId == CLERK) {
            listOf(NpcOfferRow("sale", POTION, "potion", "Potion", true, null, null, null, 300, null, null))
        } else {
            emptyList()
        }
    }

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
        const val TRAINER = 10
        const val CLERK = 11
        const val ITEM = 12
        const val POTION = 17
        const val AREA = 100
        const val PIDGEY = 16

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
