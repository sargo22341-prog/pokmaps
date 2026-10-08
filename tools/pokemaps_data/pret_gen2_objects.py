"""Nature des objets de carte de la 2e génération, d'après le script qu'ils exécutent.

- OBJECTTYPE_ITEMBALL : « itemball OBJET[, quantité] » -> objet au sol ;
- OBJECTTYPE_TRAINER : « trainer CLASSE, ID, … » -> dresseur qui combat quand il voit le joueur ;
- OBJECTTYPE_SCRIPT : un dresseur si le script lance un combat (loadtrainer), un Pokémon à combattre s'il lance
  un combat sauvage (loadwildmon), sinon un personnage. Un script commun du moteur (ObjectEvent…) qui n'est pas
  dans le fichier de la carte est celui d'un personnage.

Un objet sans combat à lui peut être l'adversaire d'un script de scène : le script le désigne avec
`setlasttalked OBJET` avant `loadtrainer` (le Rival de la Tour Cendrée). Il devient un dresseur de cette classe ;
si les scripts choisissent entre plusieurs équipes (selon le Pokémon de départ du joueur, la caméra de sécurité
déclenchée ou la progression), l'équipe reste inconnue.

Un script lu différemment en Or et en Argent (checkver) donne un objet par version : Ho-Oh et Lugia n'ont pas le
même niveau dans les deux jeux.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_models import MapObject
from .pret_source import macro_args

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo
    from .pret_gen2_scripts import ScriptFile

_ITEMBALL, _TRAINER, _SCRIPT = "OBJECTTYPE_ITEMBALL", "OBJECTTYPE_TRAINER", "OBJECTTYPE_SCRIPT"
# Combat de démonstration joué par le personnage, pas par le joueur.
_CATCH_TUTORIAL = "catchtutorial"


@dataclass(frozen=True)
class Battle:
    """Combat lancé par un script : dresseur (classe, ID) ou Pokémon sauvage (espèce, niveau)."""

    kind: str  # trainer ou pokemon
    name: str
    value: str


@dataclass(frozen=True)
class ObjectEvent:
    """Un object_event : position, apparence, type, script, et constante qui le désigne dans les scripts."""

    x: int
    y: int
    sprite: str
    object_type: str
    script: str
    const: str  # ex. BURNEDTOWER1F_RIVAL (object_const_def)
    times: frozenset[str]  # moments de la journée où l'objet est là, vide s'il est toujours là
    event_flag: str | None  # drapeau qui cache l'objet une fois levé


def classify_object(
    repo: Gen2PretRepo, script_file: ScriptFile, event: ObjectEvent, opponents: dict[str, set[Battle]]
) -> list[MapObject]:
    """Objets de carte d'un object_event : un seul, ou un par version si le script dépend de la version.

    `opponents` donne les combats de dresseur que les scripts de scène lancent contre chaque objet."""
    if event.sprite not in repo.sprites:
        raise ValueError(f"{script_file.path.name} : sprite sans image {event.sprite} ({event.script})")
    own_script = script_file.has_label(event.script)
    base = MapObject(
        event.x,
        event.y,
        "npc",
        event.sprite,
        text=event.script,
        times=event.times,
        event_flag=event.event_flag,
        const=event.const,
        cry=_cry(script_file, event.script) if own_script else None,
    )
    if event.object_type == _ITEMBALL:
        return [replace(base, kind="item", item=_itemball(script_file, event.script))]
    if event.object_type == _TRAINER and own_script:
        trainer_class, trainer_id = _trainer_line(script_file, event.script)
        return [replace(base, kind="trainer", **_trainer(repo, trainer_class, trainer_id))]
    if event.object_type not in (_SCRIPT, _TRAINER):
        raise ValueError(f"{script_file.path.name} : type d'objet inconnu {event.object_type} ({event.script})")
    scene = opponents.get(event.const, set())
    if not own_script:
        return [_scene_opponent(repo, base, scene)]
    by_version = {version: _battle(repo, script_file, event.script, symbol) for version, symbol in repo.versions}
    battles = set(by_version.values())
    if battles == {None}:
        return [_scene_opponent(repo, base, scene)]
    if len(battles) == 1:
        return [_with_battle(repo, base, battles.pop())]
    return [replace(_with_battle(repo, base, battle), version=version) for version, battle in by_version.items()]


def _cry(script_file: ScriptFile, script: str) -> str | None:
    """Pokémon dont le script fait entendre le cri, s'il n'y en a qu'un."""
    lines = script_file.reachable_lines(script, checkver=None)
    cries = {macro_args(line, "cry")[0] for line in lines if line.startswith("cry ")}
    return cries.pop() if len(cries) == 1 else None


def scene_opponents(script_file: ScriptFile) -> dict[str, set[Battle]]:
    """Objet (constante) -> combats de dresseur que lancent contre lui les scripts du fichier (setlasttalked)."""
    result: dict[str, set[Battle]] = {}
    for label in script_file.blocks:
        if "." in label:
            continue
        lines = script_file.reachable_lines(label, checkver=None)
        trainers = {
            Battle("trainer", *macro_args(line, "loadtrainer")[:2]) for line in lines if line.startswith("loadtrainer ")
        }
        wild = {
            Battle("pokemon", *macro_args(line, "loadwildmon")[:2]) for line in lines if line.startswith("loadwildmon ")
        }
        for line in lines:
            if line.startswith("applymovement "):
                target = macro_args(line, "applymovement")[0]
                for battle in wild:
                    if target.endswith(f"_{battle.name}"):
                        result.setdefault(target, set()).add(battle)
        if not trainers:
            continue
        for line in lines:
            if line.startswith("setlasttalked "):
                result.setdefault(macro_args(line, "setlasttalked")[0], set()).update(trainers)
    return result


def _scene_opponent(repo: Gen2PretRepo, base: MapObject, battles: set[Battle]) -> MapObject:
    """Personnage, ou dresseur si un script de scène le combat (équipe inconnue s'il en choisit plusieurs)."""
    if len(battles) == 1:
        return _with_battle(repo, base, next(iter(battles)))
    classes = {battle.name for battle in battles}
    if not classes:
        return base
    if len(classes) > 1:
        raise ValueError(f"{repo.root.name} : {base.text} combat plusieurs classes de dresseurs : {sorted(classes)}")
    return replace(base, kind="trainer", trainer_class=classes.pop())


def _itemball(script_file: ScriptFile, label: str) -> str:
    lines = script_file.blocks[label].lines if script_file.has_label(label) else ()
    if len(lines) != 1 or not lines[0].startswith("itemball "):
        raise ValueError(f"{script_file.path.name} : objet au sol illisible pour {label}")
    return macro_args(lines[0], "itemball")[0]


def _trainer_line(script_file: ScriptFile, label: str) -> tuple[str, str]:
    lines = script_file.blocks[label].lines
    if not lines or not lines[0].startswith("trainer "):
        raise ValueError(f"{script_file.path.name} : dresseur illisible pour {label}")
    args = macro_args(lines[0], "trainer")
    return args[0], args[1]


def _trainer(repo: Gen2PretRepo, trainer_class: str, trainer_id: str) -> dict[str, str | int]:
    """Champs d'un dresseur : sa classe et le rang de son équipe dans la classe (data/trainers/parties.asm)."""
    ids = repo.trainer_ids.get(trainer_class)
    if ids is None or trainer_id not in ids:
        raise ValueError(f"{repo.root.name} : dresseur inconnu {trainer_class}, {trainer_id}")
    return {"trainer_class": trainer_class, "trainer_number": ids.index(trainer_id) + 1}


def _battle(repo: Gen2PretRepo, script_file: ScriptFile, script: str, symbol: str) -> Battle | None:
    """Combat que lance le script dans la version de symbole `symbol` (None s'il n'en lance pas)."""
    lines = script_file.reachable_lines(script, checkver=repo.checkver(symbol))
    battles = {
        Battle(kind, *macro_args(line, command)[:2])
        for line in lines
        for command, kind in (("loadtrainer", "trainer"), ("loadwildmon", "pokemon"))
        if line.startswith(f"{command} ")
    }
    if len(battles) > 1:
        raise ValueError(f"{script_file.path.name} : {script} lance plusieurs combats : {sorted(map(str, battles))}")
    if battles and "startbattle" not in lines:
        # Le pêcheur de la Route 29 montre comment capturer un Pokémon : le combat n'est pas celui du joueur.
        if any(line.startswith(f"{_CATCH_TUTORIAL} ") for line in lines):
            return None
        raise ValueError(f"{script_file.path.name} : {script} prépare un combat sans le lancer")
    return next(iter(battles), None)


def _with_battle(repo: Gen2PretRepo, base: MapObject, battle: Battle | None) -> MapObject:
    if battle is None:
        return base
    if battle.kind == "trainer":
        return replace(base, kind="trainer", **_trainer(repo, battle.name, battle.value))
    return replace(base, kind="pokemon", pokemon=battle.name, level=int(battle.value))
