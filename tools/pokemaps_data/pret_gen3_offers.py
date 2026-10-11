"""Offres des scripts GBA, avec chemins de scénario et valeurs résolues au point du don."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_gen3_conditions import ScriptRequirement, ScriptState, script_states
from .pret_gen3_offer_tables import trade_table, tutor_moves
from .pret_gen3_script_values import number_value, range_values
from .pret_gen3_scripts import Gen3Scripts, Instruction

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo
    from .pret_gen3_maps import Gen3Event


@dataclass(frozen=True)
class Gen3Offer:
    kind: str
    item: str | None = None
    pokemon: str | None = None
    quantity: str | None = None
    move: str | None = None
    wanted: str | None = None
    source: str = ""
    paths: tuple[frozenset[ScriptRequirement], ...] = (frozenset(),)


@dataclass(frozen=True)
class ScriptOffers:
    offers: tuple[Gen3Offer, ...]
    trainers: tuple[str, ...]
    flags: tuple[str, ...]
    specials: tuple[str, ...]

    @property
    def unresolved(self) -> tuple[Gen3Offer, ...]:
        """Expressions dont la valeur vient du moteur C, à résoudre avant tout export d'offres."""
        return tuple(offer for offer in self.offers if _unresolved(offer))

    def require_resolved(self, label: str) -> None:
        if self.unresolved:
            raise ValueError(f"{label} : offres calculées par le moteur à relire : {self.unresolved}")
        if self.specials:
            raise ValueError(f"{label} : appels C à relire avant export : {self.specials}")


def _unresolved(offer: Gen3Offer) -> bool:
    symbolic = (
        (offer.item, ("ITEM_", "DECOR_")),
        (offer.pokemon, ("SPECIES_",)),
        (offer.move, ("MOVE_",)),
        (offer.wanted, ("SPECIES_",)),
    )
    if any(value is not None and not value.startswith(prefixes) for value, prefixes in symbolic):
        return True
    return offer.quantity is not None and number_value(offer.quantity, {}) is None


def _shop(scripts: Gen3Scripts, instruction: Instruction, state: ScriptState) -> list[Gen3Offer]:
    label = state.value(instruction.args[0])
    if label not in scripts.blocks:
        raise ValueError(f"{instruction.source} : liste de boutique absente : {label}")
    items: list[str] = []
    for line in scripts.blocks[label].lines:
        if line.command in {"pokemartlistend", "pokemartdecorationlistend"}:
            break
        if line.command == ".align":
            continue
        if line.command not in {".2byte", ".hword", ".byte"}:
            raise ValueError(f"{line.source} : liste de boutique illisible")
        items.extend(item for item in line.args if item not in {"ITEM_NONE", "DECOR_NONE", "0"})
        if any(item in {"ITEM_NONE", "DECOR_NONE", "0"} for item in line.args):
            break
    else:
        raise ValueError(f"{label} : liste de boutique sans fin")
    kind = "sale_decoration" if "decoration" in instruction.command else "sale"
    return [Gen3Offer(kind, item=item, source=instruction.source) for item in items]


def _direct(instruction: Instruction, state: ScriptState, scripts: Gen3Scripts) -> list[Gen3Offer]:
    command = instruction.command
    args = tuple(state.value(value) for value in instruction.args)
    source = instruction.source
    if command == "giveitem_msg":
        # La macro des remakes reçoit le texte avant l'objet, contrairement à giveitem.
        args = args[1:]
    if command in {"giveitem", "giveitem_msg", "additem", "finditem"}:
        items = _items(args[0], scripts)
        return [
            Gen3Offer("gift_item", item=item, quantity=args[1] if len(args) > 1 else "1", source=source)
            for item in items
        ]
    if command == "givemon":
        item = args[2] if len(args) > 2 and args[2] not in {"ITEM_NONE", "0"} else None
        return [Gen3Offer("gift_pokemon", item=item, pokemon=args[0], quantity=args[1], source=source)]
    if command == "giveegg":
        return [Gen3Offer("gift_egg", pokemon=args[0], quantity="5", source=source)]
    if command.startswith("pokemart") and command != "pokemartlistend":
        return _shop(scripts, instruction, state)
    if command == "givedecoration":
        return [Gen3Offer("gift_decoration", item=args[0], source=source)]
    if command in {"callstd", "gotostd"} and args[0] in {"STD_OBTAIN_ITEM", "STD_FIND_ITEM", "0", "1"}:
        return [
            Gen3Offer("gift_item", item=state.value("VAR_0x8000"), quantity=state.value("VAR_0x8001"), source=source)
        ]
    if command in {"special", "specialvar"}:
        return _special(args[-1], state, source)
    return []


def _items(value: str, scripts: Gen3Scripts) -> tuple[str, ...]:
    values = range_values(value)
    if values is None:
        return (value,)
    if len(values) > 64:
        raise ValueError(f"Trop d'objets possibles : {value}")
    items = {number: name for name, number in scripts.constants.items() if name.startswith("ITEM_")}
    if unknown := set(values) - items.keys():
        raise ValueError(f"Objets de scripts inconnus : {sorted(unknown)}")
    return tuple(items[number] for number in values)


def _special(name: str, state: ScriptState, source: str) -> list[Gen3Offer]:
    services = {
        "HealPlayerParty": "heal",
        "ScrSpecial_HealPlayerParty": "heal",
        "MoveDeleterForgetMove": "move_deleter",
        "DeletePartyMonMove": "move_deleter",
        "DeleteMonMove": "move_deleter",
        "ChangePokemonNickname": "rename_pokemon",
        "ChangeBoxPokemonNickname": "rename_pokemon",
        "StoreSelectedPokemonInDaycare": "daycare",
        "PutMonInRoute5Daycare": "daycare",
        "TeachMoveRelearnerMove": "move_relearner",
        "DisplayMoveTutorMenu": "move_relearner",
        "DaisyMassageServices": "grooming",
        "EnableNationalPokedex": "national_dex",
    }
    if name in services:
        return [Gen3Offer(services[name], source=source)]
    if name in {"ChooseMonForMoveTutor", "TeachMoveTutorMove"}:
        return [Gen3Offer("move_tutor", move=state.value("VAR_0x8005"), source=source)]
    if name == "CreateInGameTradePokemon":
        return [Gen3Offer("trade", quantity=state.value("VAR_0x8004"), source=source)]
    return []


def script_offers(
    scripts: Gen3Scripts, label: str, requirements: frozenset[ScriptRequirement] = frozenset()
) -> ScriptOffers:
    offers: dict[Gen3Offer, set[frozenset[ScriptRequirement]]] = {}
    trainers, flags, specials = set(), set(), set()
    for state in script_states(scripts, label, requirements):
        instruction = scripts.instruction(state.point)
        if instruction is None:
            raise ValueError(f"{label} : instruction disparue")
        for offer in _direct(instruction, state, scripts):
            key = replace(offer, paths=())
            offers.setdefault(key, set()).add(state.requirements)
        command, args = instruction.command, instruction.args
        if command.startswith("trainerbattle"):
            trainer = args[1] if command == "trainerbattle" else args[0]
            if trainer.startswith("TRAINER_"):
                trainers.add(trainer)
        if command in {"setflag", "clearflag", "checkflag", "goto_if_set", "goto_if_unset"}:
            flags.add(args[0])
        if command in {"special", "specialvar"}:
            specials.add(args[-1])
    merged = tuple(
        replace(offer, paths=tuple(sorted(paths, key=lambda path: sorted(path)))) for offer, paths in offers.items()
    )
    return ScriptOffers(merged, tuple(sorted(trainers)), tuple(sorted(flags)), tuple(sorted(specials)))


class Gen3Offers:
    def __init__(self, repo: Gen3PretRepo, version: str) -> None:
        self.scripts = Gen3Scripts.from_repo(repo, version)
        self._trades = trade_table(repo, version)
        self._tutors = tutor_moves(repo)
        self._cache: dict[str, ScriptOffers] = {}

    def read(self, label: str) -> ScriptOffers:
        if label in {"NULL", "0", "0x0"}:
            return ScriptOffers((), (), (), ())
        if label not in self._cache:
            result = script_offers(self.scripts, label)
            self._cache[label] = replace(result, offers=tuple(self._resolve(offer) for offer in result.offers))
        return self._cache[label]

    def read_object(self, event: Gen3Event) -> ScriptOffers:
        """Un drapeau de retrait levé masque l'objet ; ses offres exigent donc qu'il soit baissé."""
        label, flag = str(event.value("script")), str(event.value("flag"))
        if label in {"NULL", "0", "0x0"}:
            return ScriptOffers((), (), (), ())
        if number_value(flag, self.scripts.constants) == 0:
            return self.read(label)
        if not flag.startswith("FLAG_") or flag not in self.scripts.constants:
            raise ValueError(f"{label} : drapeau de présence inconnu : {flag}")
        result = script_offers(self.scripts, label, frozenset({ScriptRequirement(flag, "eq", "FALSE")}))
        return replace(
            result,
            offers=tuple(self._resolve(offer) for offer in result.offers),
            flags=tuple(sorted(set(result.flags) | {flag})),
        )

    def _resolve(self, offer: Gen3Offer) -> Gen3Offer:
        if offer.kind == "trade":
            index = number_value(offer.quantity or "", self.scripts.constants)
            if index is None or not 0 <= index < len(self._trades):
                raise ValueError(f"{offer.source} : indice d'échange illisible : {offer.quantity}")
            trade = self._trades[index]
            return replace(offer, item=trade.item, pokemon=trade.pokemon, wanted=trade.wanted, quantity=None)
        if offer.kind == "move_tutor" and offer.move:
            index = number_value(offer.move, self.scripts.constants)
            if index is not None and 0 <= index < len(self._tutors):
                return replace(offer, move=self._tutors[index])
            for prefix in ("TUTOR_MOVE_", "MOVETUTOR_"):
                if offer.move.startswith(prefix):
                    move = "MOVE_" + offer.move.removeprefix(prefix)
                    if move not in self._tutors:
                        raise ValueError(f"{offer.source} : attaque de tuteur inconnue : {move}")
                    return replace(offer, move=move)
        return offer
