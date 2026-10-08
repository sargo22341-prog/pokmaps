"""Conditions des offres de la 1re génération, lues dans les textes asm des personnages (offer_conditions).

Un texte `text_asm` teste un drapeau d'événement (CheckEvent, CheckEitherEventSet…) ou un badge (`bit BIT_…BADGE`
sur wObtainedBadges), puis saute selon les indicateurs du processeur (`jr nz`, `jp z`, `ret c`…). Chaque ligne
d'un label est un point de l'analyse ; un saut ajoute à l'état ce qu'il établit sur le dernier test. Les autres
tests (réponse du joueur, équipe pleine) ne disent pas quand l'offre existe : leurs branches gardent l'état.

La carte compte aussi : un script de carte peut changer la table de ses textes selon un événement (la Boutique de
Jadielle ne vend qu'une fois le Colis remis), et un objet masqué au départ (data/maps/toggleable_objects.asm)
n'apparaît qu'après une scène, comme M. Fuji chez lui. Les tests faits dans les routines du moteur (engine/),
hors des scripts de carte, ne sont pas lus : l'hôtesse du Club Link attend le Pokédex sans que la carte le dise.
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from .offer_conditions import ALWAYS, Condition, solve
from .pret_models import LocatedLine, NpcOffer
from .pret_source import macro_args, source_lines

if TYPE_CHECKING:
    from .pret import PretRepo

# Point d'un script : label global, rang de la ligne dans ce label.
Point = tuple[str, int]
_Next = tuple[Hashable, Condition]

_JUMPS = frozenset({"jr", "jp"})
_CALLS = frozenset({"call", "farcall", "callfar", "predef"})
_RETURN = "ret"
_ENDS = frozenset({"text_end", "done", "prompt"})
_FLAGS = frozenset({"z", "nz", "c", "nc"})
# Macros de test d'un drapeau dont le résultat est l'indicateur Z (Z : drapeau baissé). CheckEvent aussi, sauf avec
# un second argument (_multi_subject).
_ZERO_CHECKS = frozenset(
    {
        "CheckEventReuseA",
        "CheckEventAfterBranchReuseA",
        "CheckEventHL",
        "CheckEventReuseHL",
        "CheckEventForceReuseHL",
        "CheckEventAfterBranchReuseHL",
    }
)
_EITHER, _BOTH = "CheckEitherEventSet", "CheckBothEventsSet"
_BADGE_SOURCES = frozenset({"ld a, [wObtainedBadges]", "ld a, [wBeatGymFlags]"})
_EVENT_WRITES = frozenset({"SetEvent", "ResetEvent", "SetEvents", "ResetEvents", "SetEventReuseHL"})
_TOGGLES = frozenset({"predef HideObject", "predef ShowObject"})
_TEXT_POINTERS = "_TextPointers"
_TOGGLE_ON = "ON"
# Lignes remontées au plus pour trouver l'objet d'un ShowObject / HideObject.
_TOGGLE_LOOKBACK = 3


@dataclass(frozen=True)
class _Test:
    """Ce qu'établit un saut sur le dernier test : drapeaux de valeur connue (vide : rien)."""

    values: tuple[tuple[str, bool], ...] = ()


@dataclass(frozen=True)
class ObjectToggle:
    """Objet que les scripts montrent ou cachent : constante TOGGLE_…, et s'il est visible au départ."""

    toggle: str
    shown_at_start: bool


@dataclass(frozen=True)
class OfferPlace:
    """Conditions des lignes d'un texte, pour les attacher aux offres qu'il fait."""

    text: str | None
    points: dict[Point, Condition]
    own: frozenset[str]  # drapeaux levés ou baissés par le texte lui-même (Gen1Conditions.own_flags)

    def at(self, located: LocatedLine, offer: NpcOffer) -> NpcOffer:
        """L'offre faite à cette ligne du texte, avec ce qu'exige le chemin qui y mène."""
        point = (located.label, located.index)
        if point not in self.points:
            raise ValueError(f"{self.text} : offre {offer} lue à une ligne que l'analyse n'atteint pas ({located})")
        return replace(offer, condition=self.points[point].without(self.own))

    def where(self, located: list[LocatedLine], offer: NpcOffer) -> NpcOffer:
        """L'offre faite à l'une de ces lignes (service repéré par une instruction) : ce qu'exigent toutes."""
        if not located:
            raise ValueError(f"{self.text} : aucune ligne pour l'offre {offer}")
        conditions = [self.at(line, offer).condition for line in located]
        condition = conditions[0]
        for other in conditions[1:]:
            condition = condition.join(other)
        return replace(offer, condition=condition)


class Gen1Conditions:
    """Lecteur des conditions d'un dépôt pret de la 1re génération (pokered, pokeyellow)."""

    def __init__(self, repo: PretRepo) -> None:
        self.repo = repo

    def text_conditions(self, text: str | None) -> dict[Point, Condition]:
        """Condition certaine à chaque ligne atteignable quand le joueur lit le texte (constante TEXT_…)."""
        label = self.repo.text_label(text)
        if label not in self.repo.script_index.bodies:
            return {}  # texte du moteur (PickUpItemText), hors des scripts de carte : aucune offre n'y est lue
        points = solve([((label, 0), ALWAYS)], self._transfer)
        return {_point(point): condition for point, condition in points.items()}

    def offer_place(self, text: str | None) -> OfferPlace:
        points = self.text_conditions(text)
        return OfferPlace(text, points, self.own_flags(points))

    def own_flags(self, points: dict[Point, Condition]) -> frozenset[str]:
        """Drapeaux et objets que le texte lève, baisse, montre ou cache lui-même (« déjà donné ») : ils disent ce
        que le personnage a déjà fait, pas quand son offre devient possible."""
        flags: set[str] = set()
        for label, index in points:
            line = self._line(label, index)
            if line is None:
                continue
            command = line.split()[0]
            if command in _EVENT_WRITES:
                flags.update(macro_args(line, command))
            elif line in _TOGGLES and (toggle := _toggle_before(self.repo.script_index.bodies[label], index)):
                flags.add(toggle)
        return frozenset(flags)

    @cached_property
    def text_tables(self) -> dict[str, Condition]:
        """Texte (TEXT_…) -> condition de la table de textes qui le définit, quand le script de la carte choisit
        sa table selon un événement (Boutique de Jadielle). Une table que le script ne charge jamais est celle de
        l'en-tête de carte, toujours en place."""
        result: dict[str, Condition] = {}
        bodies = self.repo.script_index.bodies
        for map_script in [label for label in bodies if label.endswith("_Script")]:
            loads = self._table_loads(map_script)
            for table, condition in loads.items():
                for line in bodies.get(table, []):
                    if line.startswith("dw_const "):
                        text = macro_args(line, "dw_const")[1]
                        result[text] = result[text].join(condition) if text in result else condition
        return result

    def _table_loads(self, map_script: str) -> dict[str, Condition]:
        """Tables de textes que charge le script de la carte (ld hl, …_TextPointers…), avec leur condition."""
        points = solve([((map_script, 0), ALWAYS)], self._transfer)
        loads: dict[str, Condition] = {}
        for point, condition in points.items():
            label, index = _point(point)
            line = self._line(label, index) or ""
            table = line.removeprefix("ld hl, ")
            if line.startswith("ld hl, ") and _TEXT_POINTERS in table and table in self.repo.script_index.bodies:
                loads[table] = loads[table].join(condition) if table in loads else condition
        return loads

    def presence(self, map_label: str, position: int, place: OfferPlace) -> Condition:
        """Ce qu'exige la présence du personnage : table de textes qui le fait parler (text_tables), et objet
        masquable qu'un autre script que son texte montre ou cache (TOGGLE_… levé : visible). Un objet que seul son
        texte cache (Poké Ball donnée) n'a pas de condition : il disparaît une fois l'offre faite."""
        condition = self.text_tables.get(place.text or "", ALWAYS)
        toggle = self.object_toggles.get((map_label, position))
        if toggle and self._toggle_writers.get(toggle.toggle, frozenset()) - place.points.keys():
            condition = condition.requiring(toggle.toggle, True)
        return condition

    @cached_property
    def _toggle_writers(self) -> dict[str, frozenset[Point]]:
        """Constante TOGGLE_… -> lignes des scripts qui montrent ou cachent l'objet (predef ShowObject / HideObject)."""
        result: dict[str, set[Point]] = {}
        for label, body in self.repo.script_index.bodies.items():
            for index, line in enumerate(body):
                if line in _TOGGLES and (toggle := _toggle_before(body, index)):
                    result.setdefault(toggle, set()).add((label, index))
        return {toggle: frozenset(points) for toggle, points in result.items()}

    @cached_property
    def object_toggles(self) -> dict[tuple[str, int], ObjectToggle]:
        """(label de la carte, rang de l'object_event) -> objet que les scripts montrent ou cachent."""
        states = self._toggle_states()
        result = {}
        for path in sorted(self.repo.path("data/maps/objects").glob("*.asm")):
            label, consts = _object_consts(path)
            for index, const in enumerate(consts):
                if const in states:
                    result[(label, index)] = states[const]
        return result

    def _toggle_states(self) -> dict[str, ObjectToggle]:
        """Constante de l'objet -> constante TOGGLE_… et état de départ, dans l'ordre commun des deux fichiers.

        Jaune ajoute en fin de table des lignes « db CARTE, OBJET, ÉTAT » jamais lues par le jeu (copies de Daisy et
        de la Carte) : elles comptent pour l'alignement, et l'objet garde sa première constante."""
        objects = [
            args[-2:]
            for line in source_lines(self.repo.path("data/maps/toggleable_objects.asm"))
            for args in [_toggle_row(line)]
            if args
        ]
        toggles = [
            line.split()[1]
            for line in source_lines(self.repo.path("constants/toggle_constants.asm"))
            if line.startswith("const TOGGLE_")
        ]
        if len(objects) != len(toggles):
            raise ValueError(f"{self.repo.root.name} : {len(objects)} objets masquables pour {len(toggles)} TOGGLE_")
        result: dict[str, ObjectToggle] = {}
        for (const, state), toggle in zip(objects, toggles, strict=True):
            result.setdefault(const, ObjectToggle(toggle, state == _TOGGLE_ON))
        return result

    def _line(self, label: str, index: int) -> str | None:
        body = self.repo.script_index.bodies[label]
        return body[index] if index < len(body) else None

    def _transfer(self, point: Hashable, condition: Condition) -> list[_Next]:
        label, index = _point(point)
        result: list[_Next] = []
        for following, test in self._edges(label, index):
            refined = _apply(condition, test)
            if refined is not None:
                result.append((following, refined))
        return result

    def _edges(self, label: str, index: int) -> list[tuple[Point, _Test | None]]:
        """Points où l'exécution continue après la ligne, avec ce qu'établit chaque saut conditionnel."""
        line = self._line(label, index)
        if line is None:
            following = self.repo.script_index.following.get(label)
            return [((following, 0), None)] if following else []
        parts = line.replace(",", " ").split()
        command, args = parts[0], parts[1:]
        after = (label, index + 1)
        if command in _ENDS:
            return []
        if command not in _JUMPS and command not in _CALLS and command != _RETURN:
            return [(after, None)]
        flag = args[0] if args and args[0] in _FLAGS else None
        taken, skipped = self._tests(label, index, flag)
        target = self._target(label, args[-1]) if args and args[-1] != flag else None
        if command == _RETURN:
            return [(after, skipped)] if flag else []
        if command in _CALLS:
            return [(after, None), *([(target, taken)] if target else [])]
        edges = [(target, taken)] if target else []
        return [*edges, (after, skipped)] if flag else edges

    def _target(self, label: str, reference: str) -> Point | None:
        """Point d'arrivée d'un saut : label local (« .done ») du label courant, ou label global d'un script."""
        if reference.startswith("."):
            body = self.repo.script_index.bodies[label]
            for index, line in enumerate(body):
                if line.rstrip(":") == reference:
                    return (label, index)
            raise ValueError(f"{self.repo.root.name} : label local {reference} introuvable dans {label}")
        return (reference, 0) if reference in self.repo.script_index.bodies else None

    def _tests(self, label: str, index: int, flag: str | None) -> tuple[_Test | None, _Test | None]:
        """Ce qu'établissent le saut pris et la suite, d'après le dernier test avant la ligne."""
        subject = self._subject(label, index) if flag else None
        if subject is None or flag is None:
            return None, None
        kind, names = subject
        match kind, flag:
            case "zero", "nz" | "z":
                return _Test(((names[0], flag == "nz"),)), _Test(((names[0], flag == "z"),))
            case "carry", "c" | "nc":
                return _Test(((names[0], flag == "c"),)), _Test(((names[0], flag == "nc"),))
            case _EITHER, "z":
                return _Test(tuple((name, False) for name in names)), None
            case _EITHER, "nz":
                return None, _Test(tuple((name, False) for name in names))
            case _BOTH, "z":
                return _Test(tuple((name, True) for name in names)), None
            case _BOTH, "nz":
                return None, _Test(tuple((name, True) for name in names))
        return None, None

    def _subject(self, label: str, index: int) -> tuple[str, tuple[str, ...]] | None:
        """Dernier test d'un drapeau avant la ligne, depuis le dernier label local (point de jonction). Une
        instruction autre qu'un chargement (ld) peut changer les indicateurs : elle efface le sujet."""
        subject = None
        body = self.repo.script_index.bodies[label]
        for position in range(index):
            line = body[position]
            command = line.split()[0]
            if line.startswith("."):
                subject = None
            elif command in _ZERO_CHECKS:
                subject = ("zero", (macro_args(line, command)[0],))
            elif command in ("CheckEvent", _EITHER, _BOTH):
                subject = _multi_subject(line, command)
            elif command == "bit" and position > 0 and body[position - 1] in _BADGE_SOURCES:
                subject = ("zero", (macro_args(line, "bit")[0],))
            elif command != "ld":
                subject = None
        return subject


def _multi_subject(line: str, command: str) -> tuple[str, tuple[str, ...]]:
    args = macro_args(line, command)
    if command == "CheckEvent":
        # CheckEvent EVENT, 1 : le drapeau va dans la retenue (rrca) au lieu de l'indicateur Z.
        return ("carry" if len(args) > 1 else "zero", (args[0],))
    return (command, tuple(args[:2]))


def _toggle_before(body: list[str], index: int) -> str | None:
    """Objet que montre ou cache `predef ShowObject` / `HideObject` à la ligne `index` : la constante TOGGLE_…
    chargée juste avant (« ld a, TOGGLE_… », puis « ld [wToggleableObjectIndex], a »)."""
    for line in reversed(body[max(0, index - _TOGGLE_LOOKBACK) : index]):
        if line.startswith("ld a, TOGGLE_"):
            return line.removeprefix("ld a, ")
        if line.startswith("."):
            return None
    return None


def _toggle_row(line: str) -> list[str]:
    """Arguments d'une ligne de la table des objets masquables (toggle_object_state, ou db avant la fin)."""
    if line.startswith("toggle_object_state "):
        return macro_args(line, "toggle_object_state")
    args = macro_args(line, "db") if line.startswith("db ") else []
    return args if len(args) == 3 and args[0] != "-1" else []


def _point(point: Hashable) -> Point:
    if not (isinstance(point, tuple) and len(point) == 2 and isinstance(point[0], str)):
        raise TypeError(f"Point de script inattendu : {point!r}")
    return point


def _apply(condition: Condition, test: _Test | None) -> Condition | None:
    """État après un saut, None s'il est impossible (drapeau exigé à la fois levé et baissé)."""
    if test is None:
        return condition
    for flag, value in test.values:
        condition = condition.requiring(flag, value)
    return condition if condition.possible else None


def _object_consts(path: Path) -> tuple[str, list[str]]:
    """Label de la carte et constantes de ses objets (const_export), dans l'ordre des object_event."""
    label = None
    consts: list[str] = []
    for line in source_lines(path):
        if line.startswith("const_export "):
            consts.append(line.split()[1])
        elif line.endswith("_Object:"):
            label = line.removesuffix("_Object:")
    if label is None:
        raise ValueError(f"{path.name} : label _Object introuvable")
    return label, consts
