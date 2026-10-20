package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameVersion
import org.opensources.pokmaps.domain.model.VersionGroup

/** Choisit les fournisseurs de la branche du jeu avant de construire les définitions propres à sa version. */
internal fun guideDefinitions(game: Game): List<GuideDefinition> {
    val versionId = game.version.id
    val branch = when (game.versionGroup) {
        VersionGroup.RED_BLUE, VersionGroup.YELLOW -> kantoGuides() + sideGuides() + tipGuides()

        VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL -> johtoGuides() + sideGuides() + tipGuides()

        VersionGroup.RUBY_SAPPHIRE, VersionGroup.EMERALD ->
            gbaToolGuides() + hoennGuides() + hoennCalendarGuides() + hoennContentGuides()

        VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM -> sinnohGuides(game) + sinnohToolGuides(game)

        VersionGroup.FIRERED_LEAFGREEN -> gbaToolGuides() + remakeGuides()
    }
    return branch.filter { versionId in it.versions }
}

/** Chaque version conserve sa provenance, même lorsque les fichiers Diamant/Perle sont communs. */
internal fun sinnohGuideSources(game: Game): List<String> = requireNotNull(SINNOH_SOURCES[game.version])

private const val DIAMOND_SOURCE =
    "https://github.com/pret/pokediamond/blob/b623abef1b4dfe204ca50aab42447ac00c134290/"
private const val PLATINUM_SOURCE =
    "https://github.com/pret/pokeplatinum/blob/1dc13dcea40c04ab53f1f607de46023dc409ef20/"
private val DIAMOND_GUIDE_SOURCES = listOf(
    "arm9/src/daycare.c", "arm9/src/pokemon.c", "arm9/src/scrcmd_party.c",
    "arm9/overlays/05/asm/ov05_021EC458.s",
    "arm9/asm/unk_020603B0.s",
    "arm9/src/map_header.c", "arm9/src/gf_rtc.c", "arm9/src/scrcmd.c", "arm9/src/pokedex.c",
    "arm9/overlays/06/asm/overlay_06.s", "arm9/overlays/05/asm/ov05_021F4CF8.s",
    "files/fielddata/script/scr_seq_release/narc_0011.bin",
    "files/fielddata/script/scr_seq_release/narc_0050.bin",
    "files/fielddata/script/scr_seq_release/narc_0126.bin",
    "files/fielddata/script/scr_seq_release/narc_0148.bin",
    "files/fielddata/script/scr_seq_release/narc_0158.bin",
    "files/fielddata/script/scr_seq_release/narc_0195.bin",
    "files/fielddata/script/scr_seq_release/narc_0210.bin",
    "files/fielddata/script/scr_seq_release/narc_0230.bin",
    "files/fielddata/script/scr_seq_release/narc_0329.bin",
    "files/fielddata/script/scr_seq_release/narc_0405.bin",
    "files/fielddata/script/scr_seq_release/narc_0999.bin",
    "files/fielddata/script/scr_seq_release/narc_1036.bin",
    "files/poketool/personal/evo.json"
).map { DIAMOND_SOURCE + it }
private val PEARL_GUIDE_SOURCES = DIAMOND_GUIDE_SOURCES +
    (DIAMOND_SOURCE + "files/poketool/personal_pearl/personal.json")
private val PLATINUM_GUIDE_SOURCES = listOf(
    "src/overlay005/daycare.c", "src/daycare_save.c", "src/pokemon.c", "src/item_use_pokemon.c", "src/scrcmd_party.c",
    "src/roaming_pokemon.c", "res/field/scripts/scripts_resort_area_ribbon_syndicate_2f.s",
    "res/field/scripts/scripts_eterna_city_south_house.s",
    "src/rtc.c", "src/pokedex.c", "src/underground/mining.c", "src/overlay005/honey_tree.c",
    "res/field/scripts/scripts_route_201.s",
    "res/field/scripts/scripts_hearthome_city_gym_entrance_room.s",
    "res/field/scripts/scripts_sandgem_town_pokemon_research_lab.s",
    "res/field/scripts/scripts_valley_windworks_outside.s",
    "res/field/scripts/scripts_old_chateau_back_middle_west_room.s",
    "res/field/scripts/scripts_survival_area.s", "res/field/scripts/scripts_sunyshore_market.s",
    "res/field/scripts/scripts_jubilife_tv_1f.s", "res/field/scripts/scripts_flower_shop.s",
    "res/field/scripts/scripts_pastoria_city_southwest_house.s",
    "res/field/scripts/scripts_veilstone_city_southwest_house.s", "res/field/scripts/scripts_route_208_house.s",
    "res/field/scripts/scripts_iron_island.s",
    "res/field/scripts/scripts_distortion_world_giratina_room.s",
    "src/overlay006/wild_encounters.c", "res/battle/scripts/subscripts/subscript_pursuit.s"
).map { PLATINUM_SOURCE + it }
private val SINNOH_SOURCES = mapOf(
    GameVersion.DIAMOND to DIAMOND_GUIDE_SOURCES,
    GameVersion.PEARL to PEARL_GUIDE_SOURCES,
    GameVersion.PLATINUM to PLATINUM_GUIDE_SOURCES
)
