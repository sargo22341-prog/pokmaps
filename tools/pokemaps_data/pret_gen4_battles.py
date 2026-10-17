"""Combats de dresseurs des lieux DS : PNJ dresseurs, combats lancés par les scripts et partenaires.

Un PNJ dont le script appartient aux tranches 3000 ou 5000 est un dresseur ordinaire (pret_gen4_script_ids). Les
autres combats sont lancés par les scripts des lieux (StartTrainerBattle, StartTagBattle ; commandes 0xE5 et
0x2A0 de Diamant/Perle) : rival, Commandants et Hélio, Conseil 4, Maître, combats en duo. Leurs arguments sont
souvent des variables, lues en suivant le flux (pret_gen4_flow_values) : l'équipe du rival et celle du partenaire
restent rattachées au Pokémon de départ et au sexe du joueur qui les choisissent. Un partenaire qui suit le
joueur est fixé par une affectation de la variable lue par le moteur (VAR_PARTNER_TRAINER_ID de Platine,
0x403F de Diamant/Perle, sub_0205F368).

Chaque combat garde les conditions de la chaîne d'étapes qui y mène (pret_gen4_flow_chains), par exemple le
nombre de victoires à la Ligue qui choisit l'équipe du rival à l'Aire de Survie.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import asm_function, c_function
from .pret_gen4_flow import FIRST_BATTLE, SET_VALUE, TAG_BATTLE, TRAINER_BATTLE, Step, Value, is_var
from .pret_gen4_flow_chains import Chains, Condition
from .pret_gen4_flow_values import GENDER_SLOT, STARTER_SLOT, Choices, FlowValues, values_at
from .pret_gen4_source import metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header

# Combats dont un argument peut aussi valoir une valeur que la lecture ne borne pas, avec la raison pour laquelle
# cette valeur n'existe pas en jeu. Une entrée inemployée arrête la lecture.
_OPEN_BATTLES = {
    ("platinum", "scripts_battleground"): (
        "VAR_MAP_LOCAL_0x01 (apparence du dresseur abordé) vaut toujours l'une des treize apparences testées par "
        "Battleground_SetTrainer : la combinaison sans affectation n'existe pas en jeu."
    ),
}
_DP_ASM = "arm9/asm/unk_0205F314.s"
_DP_PARTNER = ("ldr r1, _0205F374", "_0205F374: .word 0x0000403F")
_DP_PARTNER_VAR = 0x403F
_DP_RIVAL_STARTER = ("_0205F3BC: .word 0x00000183", "add r2, r2, #0x3", "add r2, r2, #0x6")
_DP_STARTERS = frozenset({0x183, 0x186, 0x189})
_STARTERS = ("SPECIES_TURTWIG", "SPECIES_CHIMCHAR", "SPECIES_PIPLUP")
_KINDS = {TRAINER_BATTLE: "trainer", TAG_BATTLE: "tag", FIRST_BATTLE: "first"}


@dataclass(frozen=True)
class EventTrainer:
    header: int
    event: int  # rang du PNJ dans les événements du lieu
    x: int
    z: int
    y: int
    graphics: int
    hidden_flag: int
    trainer: int
    second_of_pair: bool  # second dresseur d'un combat à deux (tranche 5000)


@dataclass(frozen=True)
class BattleVariant:
    opponents: tuple[int, ...]  # un ou deux dresseurs adverses
    partner: int | None
    player_starter: int | None  # None : l'équipe ne dépend pas du Pokémon de départ du joueur
    player_gender: int | None


@dataclass(frozen=True)
class ScriptBattle:
    script_file: int
    step: str
    kind: str  # trainer (un ou deux adversaires), tag (avec partenaire) ou first (premier combat de Platine)
    variants: tuple[BattleVariant, ...]
    conditions: tuple[Condition, ...]
    open_reason: str | None


@dataclass(frozen=True)
class FollowerPartner:
    script_file: int
    step: str
    trainer: int


def read_event_trainers(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> tuple[EventTrainer, ...]:
    ids = repo.script_ids
    result = []
    for index in sorted(headers):
        for event, obj in enumerate(repo.events[headers[index].events].object_events):
            found = ids.trainer(obj.script)
            if found is not None:
                trainer, second = found
                values = (index, event, obj.x, obj.z, obj.y, obj.graphics, obj.hidden_flag, trainer, second)
                result.append(EventTrainer(*values))
    return tuple(result)


def battle_choices(repo: Gen4PretRepo) -> Choices:
    """Pokémon de départ proposés (STARTER_OPTION_* de choose_starter_app.c ; sub_0205F398 de Diamant/Perle, qui
    traite 0x183, 0x183 + 3 et le reste, 0x183 + 6) et sexes du joueur (GENDER_MALE, GENDER_FEMALE)."""
    if not repo.platinum:
        body = asm_function(read_text(repo.root / _DP_ASM), "sub_0205F398", _DP_ASM)
        if any(line not in body for line in _DP_RIVAL_STARTER):
            raise ValueError(f"{repo.root} : Pokémon de départ du rival illisibles (sub_0205F398)")
        return Choices(_DP_STARTERS, frozenset({0, 1}))
    text = read_text(repo.root / "src/choose_starter/choose_starter_app.c")
    if any(f"#define STARTER_OPTION_{index}    {name}" not in text for index, name in enumerate(_STARTERS)):
        raise ValueError(f"{repo.root} : Pokémon de départ introuvables dans choose_starter_app.c")
    species = metang_enum(repo.root / "generated/species.txt")
    genders = metang_enum(repo.root / "generated/genders.txt")
    return Choices(
        frozenset(species[name] for name in _STARTERS), frozenset({genders["GENDER_MALE"], genders["GENDER_FEMALE"]})
    )


def read_script_battles(repo: Gen4PretRepo, files: set[int]) -> tuple[ScriptBattle, ...]:
    choices = battle_choices(repo)
    used: set[tuple[str, str]] = set()
    result = []
    for index in sorted(files):
        flow = repo.flows[index]
        battles = [step for step in flow.steps.values() if _is_battle(step)]
        if not battles:
            continue
        seeds = {int(arg) for step in battles for arg in step.arguments if is_var(arg)}
        values = values_at(flow, _is_battle, seeds, None, repo.common_scripts, choices)
        chains = Chains(flow)
        reason = _OPEN_BATTLES.get((repo.variant, flow.name))
        for step in battles:
            variants, open_values = _variants(step, values, choices, flow.name)
            if open_values and reason is None:
                raise ValueError(f"{flow.name} : adversaire non lu pour {step.source}")
            if open_values:
                used.add((repo.variant, flow.name))
            kept = reason if open_values else None
            kind = _KINDS[step.command]
            result.append(ScriptBattle(index, step.source, kind, variants, chains.conditions(step.key), kept))
    if unused := {key for key in _OPEN_BATTLES if key[0] == repo.variant} - used:
        raise ValueError(f"Combats ouverts sans emploi : {sorted(unused)}")
    return tuple(result)


def _is_battle(step: Step) -> bool:
    return step.command in _KINDS


def _variants(step: Step, values: FlowValues, choices: Choices, where: str) -> tuple[tuple[BattleVariant, ...], bool]:
    """Combinaisons d'adversaires, de partenaire, de Pokémon de départ et de sexe du joueur à ce combat ; vrai en
    second si une combinaison garde un adversaire ou un partenaire non lu."""
    if step.key not in values.found:
        raise ValueError(f"{where} : combat jamais atteint : {step.source}")
    # Partenaire, premier et second adversaires ; 0 désigne l'absence (TRAINER_NONE).
    if step.command == TAG_BATTLE:
        items = step.arguments[:3]
    else:
        items = (0, step.arguments[0], step.arguments[1] if step.command == TRAINER_BATTLE else 0)
    variants: set[BattleVariant] = set()
    open_values = False
    for partner, first, second, starter, gender in values.combos(step.key, (*items, STARTER_SLOT, GENDER_SLOT)):
        if not isinstance(partner, int) or not isinstance(first, int) or not isinstance(second, int):
            open_values = True
            continue
        opponents = tuple(value for value in (first, second) if value)
        if not opponents:
            raise ValueError(f"{where} : combat sans adversaire : {step.source}")
        variants.add(BattleVariant(opponents, partner or None, _choice(starter), _choice(gender)))
    merged = _merge(_merge(variants, "player_starter", choices.starters), "player_gender", choices.genders)
    return tuple(sorted(merged, key=_variant_order)), open_values


def _choice(value: Value) -> int | None:
    """Choix lu à ce combat, ou None si aucune lecture ne le fixe sur ce chemin."""
    return value if isinstance(value, int) else None


def _variant_order(variant: BattleVariant) -> tuple[int, ...]:
    choices = (variant.partner or 0, variant.player_starter or 0, variant.player_gender or 0)
    return (*variant.opponents, *choices)


def _merge(variants: set[BattleVariant], name: str, domain: frozenset[int]) -> set[BattleVariant]:
    """Remplace par None un choix dont l'équipe ne dépend pas : toutes ses valeurs y mènent, ou il n'est pas lu."""
    groups: dict[BattleVariant, set[int | None]] = {}
    for variant in variants:
        groups.setdefault(replace(variant, **{name: None}), set()).add(getattr(variant, name))
    result: set[BattleVariant] = set()
    for base, values in groups.items():
        if None in values or values == domain:
            result.add(base)
        else:
            result |= {replace(base, **{name: value}) for value in values}
    return result


def read_follower_partners(repo: Gen4PretRepo, files: set[int]) -> tuple[FollowerPartner, ...]:
    """Affectations de la variable du partenaire qui suit le joueur, par fichier de scripts."""
    var = _partner_var(repo)
    result = []
    for index in sorted(files):
        flow = repo.flows[index]
        for step in flow.steps.values():
            if step.command == SET_VALUE and step.arguments[0] == var:
                trainer = step.arguments[1]
                if not isinstance(trainer, int) or not trainer:
                    raise ValueError(f"{flow.name} : partenaire illisible : {step.source}")
                result.append(FollowerPartner(index, step.source, trainer))
    return tuple(result)


def _partner_var(repo: Gen4PretRepo) -> int:
    if repo.platinum:
        body = c_function(read_text(repo.root / "src/system_vars.c"), "SystemVars_GetPartnerTrainerID", "system_vars.c")
        if "VAR_PARTNER_TRAINER_ID" not in body:
            raise ValueError(f"{repo.root} : variable du partenaire modifiée")
        return metang_enum(repo.root / "generated/vars_flags.txt")["VAR_PARTNER_TRAINER_ID"]
    body = asm_function(read_text(repo.root / _DP_ASM), "sub_0205F368", _DP_ASM)
    battle = c_function(read_text(repo.root / "arm9/src/scrcmd_7.c"), "ScrCmd_Unk00E5", "scrcmd_7.c")
    if any(line not in body for line in _DP_PARTNER) or "sub_0205F368" not in battle:
        raise ValueError(f"{repo.root} : variable du partenaire modifiée (sub_0205F368)")
    return _DP_PARTNER_VAR
