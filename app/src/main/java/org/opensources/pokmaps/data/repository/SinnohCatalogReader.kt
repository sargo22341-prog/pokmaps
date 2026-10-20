package org.opensources.pokmaps.data.repository

import org.json.JSONArray
import org.json.JSONObject
import org.opensources.pokmaps.domain.sinnoh.BattleConfiguration
import org.opensources.pokmaps.domain.sinnoh.BattleSeries
import org.opensources.pokmaps.domain.sinnoh.FactoryPool
import org.opensources.pokmaps.domain.sinnoh.MiningTreasure
import org.opensources.pokmaps.domain.sinnoh.SinnohBattles
import org.opensources.pokmaps.domain.sinnoh.SinnohFrontier
import org.opensources.pokmaps.domain.sinnoh.SinnohUnderground
import org.opensources.pokmaps.domain.sinnoh.UndergroundGood
import org.opensources.pokmaps.domain.sinnoh.UndergroundPrice
import org.opensources.pokmaps.domain.sinnoh.UndergroundTrap

internal fun sinnohRows(array: JSONArray, count: Int): List<JSONObject> {
    require(array.length() == count)
    return List(count) { array.getJSONObject(it) }
}

internal fun sinnohUnderground(value: JSONObject): SinnohUnderground {
    val row = value.getJSONObject("underground")
    val goods = sinnohRows(row.getJSONArray("goods"), 132).map {
        UndergroundGood(
            it.getInt("id"),
            it.getString("name"),
            it.getInt("width"),
            it.getInt("depth"),
            price(it),
            it.getInt("money"),
            it.getBoolean("national"),
            !it.getString("identifier").endsWith("_UNUSED") && it.getInt("id") !in 129..132
        )
    }
    val traps = sinnohRows(row.getJSONArray("traps"), 27).map {
        UndergroundTrap(it.getInt("id"), it.getString("name"), price(it))
    }
    val mining = sinnohRows(value.getJSONArray("mining"), 58).map {
        MiningTreasure(it.getInt("id"), it.getString("name"), integers(it.getJSONArray("weights"), 4))
    }
    require(goods.map { it.id }.toSet() == (7..138).toSet())
    require(traps.map { it.id }.toSet() == (1..8).toSet() + (11..14) + (18..31) + 33)
    require(mining.map { it.id }.toSet() == (1..59).toSet() - 22)
    return SinnohUnderground(goods, traps, mining)
}

internal fun sinnohBattles(value: JSONObject, platinum: Boolean): SinnohBattles {
    val row = value.getJSONObject("battles")
    val configurations = configurations(row.getJSONArray("sets"), 950)
    val trainers = row.getJSONArray("trainers")
    require(trainers.length() == if (platinum) 315 else 307)
    val pools = List(trainers.length()) { index ->
        val pool = trainers.getJSONArray(index)
        require(pool.length() <= 100)
        integers(pool, pool.length()).also { require(it.all { id -> id in configurations }) }
    }
    require(
        pools.indices.filter { pools[it].isEmpty() }.toSet() ==
            if (platinum) setOf(307, 308, 309, 310) else emptySet<Int>()
    )
    require(row.has("frontier") == platinum)
    return SinnohBattles(
        configurations,
        pools,
        series(row.getJSONArray("tower_ranges")),
        if (platinum) frontier(row.getJSONObject("frontier")) else null
    )
}

private fun configurations(array: JSONArray, count: Int): Map<Int, BattleConfiguration> {
    val rows = sinnohRows(array, count).map {
        val moves = integers(it.getJSONArray("moves"), 4)
        val names = it.getJSONArray("move_names")
        require(names.length() == moves.count { move -> move != 0 })
        BattleConfiguration(
            it.getInt("id"), it.getInt("species"), it.getString("name"), moves,
            List(names.length()) { i -> names.getString(i) }, it.getString("item_name"),
            it.getString("nature_name"), it.getInt("evs"), it.getInt("form")
        )
    }
    require(rows.map { it.id }.toSet() == (1..count).toSet())
    return rows.associateBy { it.id }
}

private fun frontier(row: JSONObject): SinnohFrontier {
    val ranges = row.getJSONObject("ranges")
    val factory = row.getJSONObject("factory")
    val hall = row.getJSONObject("hall")
    val ranks = hall.getJSONArray("ranks")
    require(ranks.length() == 10)
    return SinnohFrontier(
        series(ranges.getJSONArray("castle")),
        series(ranges.getJSONArray("arcade")),
        series(ranges.getJSONArray("factory")),
        factoryPools(factory.getJSONArray("level50")),
        factoryPools(factory.getJSONArray("open_player")),
        factoryPools(factory.getJSONArray("open_opponent")),
        configurations(hall.getJSONArray("sets"), 477).values.toList(),
        List(10) { i -> range(ranks.getJSONArray(i), 1, 477) }
    )
}

private fun factoryPools(array: JSONArray): List<FactoryPool> = sinnohRows(array, 10).map {
    FactoryPool(
        it.getInt("trainer_limit"),
        it.getInt("min"),
        it.getInt("max"),
        it.getInt("ivs"),
        it.getBoolean("upgrade")
    )
}

private fun series(array: JSONArray): List<BattleSeries> = sinnohRows(array, 8).map {
    BattleSeries(
        it.getInt("series"),
        range(it.getJSONArray("ordinary"), 0, 299),
        range(it.getJSONArray("last"), 0, 299)
    )
}.also { require(it.map { row -> row.number } == (1..8).toList()) }

private fun range(array: JSONArray, minimum: Int, maximum: Int): IntRange {
    val values = integers(array, 2)
    require(values[0] in minimum..maximum && values[1] in values[0]..maximum)
    return values[0]..values[1]
}

private fun price(row: JSONObject): UndergroundPrice = UndergroundPrice(
    row.getInt("sphere"),
    row.getInt("min_size"),
    row.getInt("max_size")
)

private fun integers(array: JSONArray, count: Int): List<Int> {
    require(array.length() == count)
    return List(count) { array.getInt(it) }
}
