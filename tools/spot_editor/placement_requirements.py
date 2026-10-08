"""Nombre de marqueurs requis avant de sauvegarder chaque portée éditée."""

from collections.abc import Mapping

from pokemaps_data.map_spots import TerrainKey

from .catalog import EditorCatalog, EditorMap, Family, required_spots, used_by_app
from .session import Shortfall, SpotSession


def placement_shortfalls(catalog: EditorCatalog, families: list[Family], session: SpotSession) -> list[Shortfall]:
    maps = {(family.identifier, found.identifier): found for family in families for found in catalog.maps(family)}
    return session.shortfalls(
        lambda key: _required(catalog, families, session, maps.get((key.family, key.map_identifier)), key)
    )


def _required(
    catalog: EditorCatalog, families: list[Family], session: SpotSession, editor_map: EditorMap | None, key: TerrainKey
) -> tuple[str, int]:
    if key.version_group:
        family = next(family for family in families if family.identifier == key.family)
        editor_map = catalog.version_map(family, key.map_identifier, key.version_group)
    if editor_map is None:
        return key.map_identifier, 0
    generated = catalog.generated_spots(editor_map)

    def has(kind: str) -> bool:
        terrain = TerrainKey(key.family, key.map_identifier, kind, key.version_group)
        return bool(session.effective_points(terrain, generated[kind]))

    if not used_by_app(key.kind, has("grass"), has("floor")):
        return editor_map.name, 0
    return editor_map.name, required_spots(catalog.encounters(editor_map), key.kind)


def shortfall_text(shortfalls: list[Shortfall], labels: Mapping[str, str]) -> str:
    lines = "\n".join(
        f"• {item.map_name} — {labels[item.key.kind]} : {item.points} emplacement(s) pour {item.required} Pokémon"
        for item in shortfalls
    )
    return (
        f"Ces terrains ont moins d'emplacements que de Pokémon à placer :\n\n{lines}\n\n"
        "L'application les rangera en grille au milieu du terrain. Enregistrer quand même ?"
    )
