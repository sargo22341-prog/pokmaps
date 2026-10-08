"""Lecture des cartes de la 2e génération : blocs, connexions, warps, panneaux et objets.

Les événements d'une carte sont dans maps/<Carte>.asm, sous le label <Carte>_MapEvents. Un objet de carte désigne
un label de script (pas une constante de texte comme en 1re génération) : on lit ce script pour savoir si c'est
un objet au sol (itemball), un dresseur (trainer, ou loadtrainer pour un champion), un Pokémon à combattre
(loadwildmon) ou un personnage. MapObject.text garde ce label : il identifie le personnage dans tools/data/.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .pret_gen2_objects import ObjectEvent, classify_object, scene_opponents
from .pret_gen2_scripts import ScriptFile, check_unconditional
from .pret_models import Connection, MapObject, PretMap, Sign, Warp
from .pret_source import annotated_lines, macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo, MapHeader

# Sprites qui montrent ce que le joueur a choisi : les décorations de sa chambre (engine/overworld/decorations.asm)
# et les Pokémon qu'il a confiés à la Pension (GetMonSprite). Les objets qui les portent restent cachés tant que le
# joueur n'a rien posé ni confié : ils ne sont pas des personnages de la carte.
PLAYER_DEPENDENT_SPRITES = frozenset(
    {
        "SPRITE_CONSOLE",
        "SPRITE_DOLL_1",
        "SPRITE_DOLL_2",
        "SPRITE_BIG_DOLL",
        "SPRITE_DAY_CARE_MON_1",
        "SPRITE_DAY_CARE_MON_2",
    }
)
# Script qui donne leur apparence de départ aux sprites variables (engine/events/std_scripts.asm).
_INITIAL_SPRITES_SCRIPT = "InitializeEventsScript"
_HIDDEN_ITEM = "BGEVENT_ITEM"
# Commande de script qui envoie le joueur sur une carte ; vers NONE (groupe 0), le moteur garde le joueur sur place
# (MAPSETUP_BADWARP, Script_warp).
_SCRIPT_WARP, _NO_MAP = "warp", "NONE"
# Valeur « toujours » des horaires et du drapeau d'un object_event, et moments de la journée (shift_const MORN…).
_ALWAYS = "-1"
_TIMES_OF_DAY = frozenset({"MORN", "DAY", "NITE"})
_DAY = "DAY"
# Objets que l'on ne fusionne pas : chacun est une rencontre ou un objet à ramasser.
_ALWAYS_SINGLE = frozenset({"item", "hidden_item", "trainer", "pokemon"})


def read_maps(repo: Gen2PretRepo) -> dict[str, PretMap]:
    """Toutes les cartes du jeu, indexées par constante."""
    connections = _connections(repo)
    sprites = _initial_variable_sprites(repo)
    result = {}
    for const, header in repo.headers.items():
        if header.label not in repo.script_files:
            raise ValueError(f"{repo.root.name} : événements introuvables pour {header.label}")
        script_file = repo.script_files[header.label]
        warps, signs, objects = _events(repo, script_file, header, sprites)
        result[const] = PretMap(
            const,
            header.number,
            header.label,
            header.width,
            header.height,
            header.tileset,
            _blocks(repo, header),
            header.border_block,
            header.is_outdoor,
            connections.get(const, []),
            warps,
            signs,
            objects,
            _script_warps(repo, script_file),
        )
    return result


def _script_warps(repo: Gen2PretRepo, script_file: ScriptFile) -> list[str]:
    """Cartes où les scripts de la carte envoient le joueur (« warp CARTE, x, y »)."""
    targets = {
        macro_args(line, _SCRIPT_WARP)[0]
        for block in script_file.blocks.values()
        for line in block.lines
        if line.startswith(f"{_SCRIPT_WARP} ")
    }
    targets.discard(_NO_MAP)
    if unknown := sorted(targets - repo.headers.keys()):
        raise ValueError(f"{script_file.path.name} : warp de script vers une carte inconnue : {unknown}")
    return sorted(targets)


def _blocks(repo: Gen2PretRepo, header: MapHeader) -> bytes:
    if header.label not in repo.block_files:
        raise ValueError(f"{repo.root.name} : blocs introuvables pour {header.label}")
    data = repo.block_files[header.label].read_bytes()
    if len(data) != header.width * header.height:
        raise ValueError(f"{header.label} : {len(data)} blocs pour {header.width} × {header.height}")
    count = repo.tilesets[header.tileset].metatile_count()
    if max(data) >= count:
        raise ValueError(f"{header.label} : métatuile {max(data)} absente de {header.tileset} ({count})")
    return data


def _connections(repo: Gen2PretRepo) -> dict[str, list[Connection]]:
    """Constante de carte -> connexions vers ses voisines (data/maps/attributes.asm)."""
    result: dict[str, list[Connection]] = {}
    current = None
    for line in source_lines(repo.path("data/maps/attributes.asm")):
        if line.startswith("map_attributes "):
            current = macro_args(line, "map_attributes")[1]
        elif line.startswith("connection ") and current:
            direction, _, target, offset = macro_args(line, "connection")
            result.setdefault(current, []).append(Connection(direction, target, int(offset)))
    return result


def _initial_variable_sprites(repo: Gen2PretRepo) -> dict[str, str]:
    """Sprite variable (SPRITE_WEIRD_TREE…) -> apparence donnée au début de la partie."""
    script = ScriptFile(repo.path("engine/events/std_scripts.asm"))
    return {
        args[0]: args[1]
        for args in (
            macro_args(line, "variablesprite")
            for line in script.reachable_lines(_INITIAL_SPRITES_SCRIPT, checkver=None)
            if line.startswith("variablesprite ")
        )
    }


def _events(
    repo: Gen2PretRepo, script_file: ScriptFile, header: MapHeader, sprites: dict[str, str]
) -> tuple[list[Warp], list[Sign], list[MapObject]]:
    warps: list[Warp] = []
    signs: list[Sign] = []
    objects: list[MapObject] = []
    object_events: list[list[str]] = []
    for line, comment in _event_lines(script_file, header.label):
        if line.startswith("warp_event "):
            x, y, target, number = macro_args(line, "warp_event")
            # Les warps gardent leur rang même inaccessibles : les autres cartes s'y réfèrent par leur numéro.
            warps.append(Warp(int(x), int(y), target, parse_int(number), comment != "inaccessible"))
        elif line.startswith("bg_event "):
            x, y, kind, script = macro_args(line, "bg_event")
            if kind == _HIDDEN_ITEM:
                objects.append(MapObject(int(x), int(y), "hidden_item", item=_hidden_item(script_file, script)))
            else:
                signs.append(Sign(int(x), int(y), script))
        elif line.startswith("object_event "):
            object_events.append(macro_args(line, "object_event"))
    return warps, signs, objects + _objects(repo, script_file, object_events, sprites)


def _event_lines(script_file: ScriptFile, label: str) -> list[tuple[str, str]]:
    """Lignes du bloc <Carte>_MapEvents, avec leur commentaire (« inaccessible » pour certains warps)."""
    lines = annotated_lines(script_file.path)
    start = next((i for i, (code, _) in enumerate(lines) if code == f"{label}_MapEvents:"), None)
    if start is None:
        raise ValueError(f"{script_file.path.name} : label {label}_MapEvents introuvable")
    result = []
    for code, comment in lines[start + 1 :]:
        check_unconditional(code, script_file.path)
        if code.endswith(":"):
            break
        result.append((code, comment))
    return result


def _hidden_item(script_file: ScriptFile, label: str) -> str:
    """Objet caché d'un bg_event BGEVENT_ITEM : « hiddenitem OBJET, ÉVÉNEMENT »."""
    lines = script_file.blocks[label].lines if script_file.has_label(label) else ()
    if len(lines) != 1 or not lines[0].startswith("hiddenitem "):
        raise ValueError(f"{script_file.path.name} : objet caché illisible pour {label}")
    return macro_args(lines[0], "hiddenitem")[0]


def _objects(
    repo: Gen2PretRepo, script_file: ScriptFile, object_events: list[list[str]], sprites: dict[str, str]
) -> list[MapObject]:
    """Objets de carte des object_event, que les scripts désignent par les constantes de object_const_def."""
    consts = _object_consts(script_file)
    # Quelques fichiers déclarent des constantes de plus (objets propres à Cristal) : elles suivent les autres.
    if len(consts) < len(object_events):
        raise ValueError(f"{script_file.path.name} : {len(consts)} constantes pour {len(object_events)} objets")
    opponents = scene_opponents(script_file)
    objects: list[MapObject] = []
    for const, args in zip(consts, object_events, strict=False):
        if len(args) != 13:
            raise ValueError(f"{script_file.path.name} : object_event non pris en charge : {args}")
        if args[2] in PLAYER_DEPENDENT_SPRITES:
            continue
        x, y, sprite, object_type, script, flag = int(args[0]), int(args[1]), args[2], args[9], args[11], args[12]
        times = _appearance_times(args[6], args[7], script_file)
        event_flag = None if flag == _ALWAYS else flag
        event = ObjectEvent(x, y, sprites.get(sprite, sprite), object_type, script, const, times, event_flag)
        objects += classify_object(repo, script_file, event, opponents)
    return _daytime_objects(objects, script_file)


def _daytime_objects(objects: list[MapObject], script_file: ScriptFile) -> list[MapObject]:
    """Un personnage par script là où il est la journée, comme la carte, rendue de jour.

    Un même script sert parfois plusieurs object_event selon le moment de la journée : au même endroit (le
    pharmacien du Casino, le jour et la nuit), ils ne font qu'un ; ailleurs (Maman, le matin à la cuisine), seuls
    ceux présents la journée restent, si le script en a un. Les objets sans script à eux (ObjectEvent du moteur)
    sont des personnages différents."""
    by_script: dict[str, list[MapObject]] = {}
    for obj in objects:
        if obj.text and script_file.has_label(obj.text) and obj.kind not in _ALWAYS_SINGLE:
            by_script.setdefault(obj.text, []).append(obj)
    # Objet d'origine -> ce qu'il devient (None : écarté).
    outcome: dict[int, MapObject | None] = {}
    for group in by_script.values():
        if len(group) < 2 or not any(obj.times for obj in group):
            continue
        outcome |= dict.fromkeys(map(id, group))
        places: dict[tuple[int, int, str, str | None], list[MapObject]] = {}
        for obj in group:
            places.setdefault((obj.x, obj.y, obj.kind, obj.sprite), []).append(obj)
        by_day = [same for same in places.values() if any(_present_by_day(obj) for obj in same)]
        for same_place in by_day or list(places.values()):
            outcome[id(same_place[0])] = replace(same_place[0], times=_union_times(same_place))
    result = []
    for obj in objects:
        kept = outcome.get(id(obj), obj)
        if kept is not None:
            result.append(kept)
    return result


def _present_by_day(obj: MapObject) -> bool:
    return not obj.times or _DAY in obj.times


def _union_times(objects: list[MapObject]) -> frozenset[str]:
    """Moments de présence réunis (vide : toujours là, si l'un des objets l'est)."""
    if any(not obj.times for obj in objects):
        return frozenset()
    return frozenset().union(*(obj.times for obj in objects))


def _appearance_times(first: str, second: str, script_file: ScriptFile) -> frozenset[str]:
    """Moments de la journée où l'objet apparaît (vide : toujours). « -1, MORN | DAY » : le matin et le jour ; une
    plage horaire (« h1, h2 ») n'est employée par aucune carte d'Or et d'Argent et arrête la lecture."""
    if first != _ALWAYS:
        raise ValueError(f"{script_file.path.name} : plage horaire d'objet non prise en charge : {first}, {second}")
    if second == _ALWAYS:
        return frozenset()
    times = frozenset(name.strip() for name in second.split("|"))
    if unknown := times - _TIMES_OF_DAY:
        raise ValueError(f"{script_file.path.name} : moment de la journée inconnu : {sorted(unknown)}")
    return times


def _object_consts(script_file: ScriptFile) -> list[str]:
    """Constantes des objets de la carte (object_const_def), dans l'ordre de leurs object_event."""
    result: list[str] = []
    started = False
    for line in source_lines(script_file.path):
        if line == "object_const_def":
            started = True
        elif started and line.startswith("const "):
            result.append(line.split()[1])
        elif started:
            break
    return result
