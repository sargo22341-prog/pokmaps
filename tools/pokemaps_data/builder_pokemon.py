"""Tables des Pokémon : fiches, données propres à chaque jeu, types, statistiques, évolutions et œufs."""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from .games import PretFormat
from .pokeapi import ENGLISH, FRENCH, clean_text, optional_int, value_at
from .pret_gen3_evolution import EvolutionRules, read_evolution_rules
from .pret_species import SpeciesProfile, read_species_profiles

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Stats affichées par génération : la 1re génération a une seule stat « Spécial » (id 9).
GEN1_STATS = (1, 2, 3, 6, 9)
MODERN_STATS = (1, 2, 3, 4, 5, 6)
STAT_NAME_FALLBACK = {9: "Spécial"}
# Les œufs (et donc les groupes d'œufs) apparaissent en 2e génération.
BREEDING_GENERATION = 2

# Colonnes de pokemon_evolution (PokéAPI) : identification de la ligne, puis conditions écrites dans la base. Toute
# autre condition renseignée dans un jeu configuré arrête la génération plutôt que d'être perdue.
_EVOLUTION_KEYS = frozenset({"id", "evolved_species_id", "evolution_trigger_id", "version_group_id", "is_default"})
_EVOLUTION_CONDITIONS = frozenset(
    {
        "minimum_level",
        "trigger_item_id",
        "held_item_id",
        "minimum_happiness",
        "time_of_day",
        "known_move_id",
        "trade_species_id",
        "minimum_beauty",
        "relative_physical_stats",
        "condition_expression",
        "percentage_chance",
    }
)
# Formes avant et après l'évolution : sans effet quand c'est la forme par défaut de l'espèce.
_FORM_COLUMNS = frozenset({"required_pokemon_form_id", "evolved_pokemon_form_id"})
# Conditions de PokéAPI qui départagent selon la personnalité du Pokémon (Chenipotte : Armulys ou Blindalys).
PERSONALITY_EXPRESSIONS = frozenset({"PID 16 >> 10 % 4 <=", "PID 16 >> 10 % 5 >="})


class PokemonTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    def stat_table(self) -> list[tuple]:
        names = self.api.names("stat_names", "stat_id")
        used = set(GEN1_STATS if 1 in self.builder.generations else ()) | (
            set(MODERN_STATS) if self.builder.max_generation > 1 else set()
        )
        return [
            (int(row["id"]), row["identifier"], names.get(int(row["id"])) or STAT_NAME_FALLBACK[int(row["id"])])
            for row in self.api.table("stats")
            if int(row["id"]) in used
        ]

    def growth_rate_table(self) -> list[tuple]:
        names = self.api.names("growth_rate_prose", "growth_rate_id")
        return [(int(row["id"]), row["identifier"], names[int(row["id"])]) for row in self.api.table("growth_rates")]

    def pokemon_table(self) -> list[tuple]:
        """Identité et attributs communs à tous les jeux ; ceux qui changent d'un jeu à l'autre sont dans
        pokemon_version_group_rows et egg_group_rows."""
        self._check_common_attributes()
        names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
        genus_fr = self.api.names("pokemon_species_names", "pokemon_species_id", column="genus")
        names_en = self.api.names("pokemon_species_names", "pokemon_species_id", language=ENGLISH)
        sizes = {int(row["id"]): row for row in self.api.table("pokemon")}
        descriptions = self._descriptions()
        rows = []
        for species_id, row in sorted(self.builder.species.items()):
            size = sizes[self.builder.default_pokemon[species_id]]
            # L'espèce d'origine d'une génération ultérieure (Ptiravi pour Leveinard) n'est pas dans la base.
            evolves_from = optional_int(row["evolves_from_species_id"])
            rows.append(
                (
                    species_id,
                    row["identifier"],
                    names_fr[species_id],
                    names_en[species_id],
                    genus_fr[species_id],
                    int(row["generation_id"]),
                    evolves_from if evolves_from in self.builder.species else None,
                    int(row["evolution_chain_id"]),
                    int(row["gender_rate"]),
                    int(row["growth_rate_id"]),
                    int(size["height"]),
                    int(size["weight"]),
                    int(row["is_legendary"]),
                    int(row["is_mythical"]),
                    int(row["is_baby"]),
                    *descriptions.get(species_id, (None, None)),
                )
            )
        return rows

    @cached_property
    def profiles(self) -> dict[int, dict[int, SpeciesProfile]]:
        """Groupe de versions -> espèce -> ses données de base dans le jeu, lues dans pret pour chaque espèce que
        la génération du jeu connaît."""
        identifiers = {row["identifier"]: species_id for species_id, row in self.builder.species.items()}
        result = {}
        for vg in self.builder.vg_ids:
            game = self.builder.game_of(vg)
            read = read_species_profiles(self.builder.pret_root(game, "les données de base des espèces"), game)
            if unknown := sorted(read.keys() - identifiers.keys()):
                raise ValueError(f"Espèces pret inconnues de PokéAPI dans {game.version_group} : {unknown}")
            profiles = {identifiers[name]: profile for name, profile in read.items()}
            expected = set(self._species_of_generation(self.builder.vg_generation[vg]))
            breeds = self.builder.vg_generation[vg] >= BREEDING_GENERATION
            if profiles.keys() != expected or any((p.breeding is not None) != breeds for p in profiles.values()):
                raise ValueError(f"Données de base incomplètes ou inattendues dans {game.version_group}")
            result[vg] = profiles
        return result

    def pokemon_version_group_rows(self) -> list[tuple]:
        """(espèce, groupe de versions, taux de capture, cycles d'éclosion ou None sans œufs)."""
        return sorted(
            (species_id, vg, profile.capture_rate, profile.breeding.hatch_counter if profile.breeding else None)
            for vg, profiles in self.profiles.items()
            for species_id, profile in profiles.items()
        )

    @cached_property
    def egg_group_rows(self) -> list[tuple[int, int, int]]:
        """(espèce, groupe de versions, groupe d'œufs) des jeux qui connaissent la reproduction."""
        groups = {row["identifier"]: int(row["id"]) for row in self.api.table("egg_groups")}
        return sorted(
            (species_id, vg, groups[group])
            for vg, profiles in self.profiles.items()
            for species_id, profile in profiles.items()
            if profile.breeding is not None
            for group in profile.breeding.egg_groups
        )

    def _check_common_attributes(self) -> None:
        """Arrête la génération si le sexe ou la courbe d'expérience d'une espèce (une seule valeur, celle de
        PokéAPI) diffère dans un jeu : il faudrait alors les écrire par groupe de versions."""
        growth_rates = {row["identifier"]: int(row["id"]) for row in self.api.table("growth_rates")}
        for vg, profiles in self.profiles.items():
            for species_id, profile in profiles.items():
                row = self.builder.species[species_id]
                expected = (int(row["growth_rate_id"]), int(row["gender_rate"]))
                gender = profile.breeding.gender_rate if profile.breeding else expected[1]
                if (growth_rates[profile.growth_rate], gender) != expected:
                    raise ValueError(f"Sexe ou courbe d'expérience propre au groupe {vg} pour l'espèce {species_id}")

    def egg_group_table(self) -> list[tuple]:
        names = self.api.names("egg_group_prose", "egg_group_id")
        used = {group for _, _, group in self.egg_group_rows}
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])])
            for row in self.api.table("egg_groups")
            if int(row["id"]) in used
        ]

    def _descriptions(self) -> dict[int, tuple[str, str]]:
        """Description française du Pokédex et nom du jeu d'où elle vient : celle d'un jeu configuré si elle
        existe, sinon la plus ancienne (PokéAPI n'a aucun texte français de la 1re à la 3e génération)."""
        preferred = set(self.builder.version_ids)
        versions = self.api.names("version_names", "version_id")
        best: dict[int, tuple[tuple[int, int], str]] = {}
        for row in self.api.table("pokemon_species_flavor_text"):
            if int(row["language_id"]) != FRENCH:
                continue
            species_id, version = int(row["species_id"]), int(row["version_id"])
            rank = (0 if version in preferred else 1, version)
            if species_id not in best or rank < best[species_id][0]:
                best[species_id] = (rank, clean_text(row["flavor_text"]))
        if unnamed := sorted({version for (_, version), _ in best.values()} - versions.keys()):
            raise ValueError(f"Versions sans nom français pour les descriptions du Pokédex : {unnamed}")
        return {species_id: (text, versions[version]) for species_id, ((_, version), text) in best.items()}

    def pokemon_type_table(self) -> list[tuple]:
        current: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for row in self.api.table("pokemon_types"):
            current[int(row["pokemon_id"])].append((int(row["slot"]), int(row["type_id"])))
        past: dict[int, dict[int, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        for row in self.api.table("pokemon_types_past"):
            past[int(row["pokemon_id"])][int(row["generation_id"])].append((int(row["slot"]), int(row["type_id"])))
        rows = []
        for generation in self.builder.generations:
            for species_id in self._species_of_generation(generation):
                pokemon_id = self.builder.default_pokemon[species_id]
                types = current[pokemon_id]
                # Types passés : « jusqu'à la génération N, le Pokémon avait ces types ».
                for until in sorted(past[pokemon_id]):
                    if until >= generation:
                        types = past[pokemon_id][until]
                        break
                rows += [(species_id, generation, slot, type_id) for slot, type_id in sorted(types)]
        return rows

    def pokemon_stat_table(self) -> list[tuple]:
        current: dict[tuple[int, int], int] = {
            (int(row["pokemon_id"]), int(row["stat_id"])): int(row["base_stat"])
            for row in self.api.table("pokemon_stats")
        }
        past: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for row in self.api.table("pokemon_stats_past"):
            key = (int(row["pokemon_id"]), int(row["stat_id"]))
            past[key].append((int(row["generation_id"]), int(row["base_stat"])))
        rows = []
        for generation in self.builder.generations:
            stats = GEN1_STATS if generation == 1 else MODERN_STATS
            for species_id in self._species_of_generation(generation):
                pokemon_id = self.builder.default_pokemon[species_id]
                for stat in stats:
                    value = value_at(past.get((pokemon_id, stat), []), generation, current.get((pokemon_id, stat)))
                    if value is None:
                        raise ValueError(
                            f"Stat {stat} manquante pour le Pokémon {species_id} (génération {generation})"
                        )
                    rows.append((species_id, generation, stat, value))
        return rows

    def _species_of_generation(self, generation: int) -> list[int]:
        """Espèces déjà apparues à `generation`, triées par numéro."""
        return [
            species_id
            for species_id, row in sorted(self.builder.species.items())
            if int(row["generation_id"]) <= generation
        ]

    @cached_property
    def evolution_rows(self) -> list[tuple]:
        triggers = {int(row["id"]): row["identifier"] for row in self.api.table("evolution_triggers")}
        by_target: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row in self.api.table("pokemon_evolution"):
            by_target[int(row["evolved_species_id"])].append(row)
        rows = []
        for vg in self.builder.vg_ids:
            rules = self._evolution_rules(vg)
            for target, candidates in sorted(by_target.items()):
                source = self.builder.species.get(target, {}).get("evolves_from_species_id")
                if target not in self.builder.species or not source:
                    continue
                if int(self.builder.species[target]["generation_id"]) > self.builder.vg_generation[vg]:
                    continue
                methods = self._evolution_methods(vg, candidates)
                for row in methods:
                    _check_represented(row, self._default_forms)
                rows += [
                    (vg, int(source), target, triggers[int(row["evolution_trigger_id"])], *_conditions(row, rules))
                    for row in methods
                    if rules is None or rules.time_of_day or not row["time_of_day"]
                ]
        return [(index, *row) for index, row in enumerate(rows, start=1)]

    @cached_property
    def _default_forms(self) -> frozenset[str]:
        """Formes par défaut des espèces (PokéAPI les cite parfois comme forme requise d'une évolution)."""
        defaults = set(self.builder.default_pokemon.values())
        return frozenset(
            row["id"]
            for row in self.api.table("pokemon_forms")
            if row["is_default"] == "1" and int(row["pokemon_id"]) in defaults
        )

    def _evolution_rules(self, vg: int) -> EvolutionRules | None:
        """Règles du moteur de ce jeu, lues dans pret ; None pour garder les conditions de PokéAPI.

        PokéAPI donne le seuil de bonheur des jeux récents (160) : le moteur de la 2e génération demande 220
        (HAPPINESS_TO_EVOLVE, engine/pokemon/evolve.asm), comme celui de la 3e (pret_gen3_evolution.py), où Rouge Feu
        et Vert Feuille n'ont en plus aucune évolution de jour ou de nuit."""
        game = self.builder.game_of(vg)
        match game.pret_format:
            case PretFormat.GEN1:
                return None
            case PretFormat.GEN2:
                return EvolutionRules(self.builder.gen2_repo(game, "le bonheur d'évolution").happiness_to_evolve, True)
            case PretFormat.GEN3:
                return read_evolution_rules(self.builder.pret_root(game, "les règles d'évolution"), game.pret_repo)

    def _evolution_methods(self, vg: int, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
        """Méthodes valables dans ce jeu : celles introduites au plus tard dans ce groupe de versions,
        en ne gardant que la plus récente (la méthode peut changer d'un jeu à l'autre)."""
        order = self.builder.vg_order
        valid = [row for row in candidates if order[int(row["version_group_id"])] <= order[vg]]
        if not valid:
            return []
        latest = max(order[int(row["version_group_id"])] for row in valid)
        return [row for row in valid if order[int(row["version_group_id"])] == latest]


def _check_represented(row: dict[str, str], default_forms: frozenset[str]) -> None:
    """Arrête la génération si l'évolution a une condition de PokéAPI que la base ne sait pas écrire."""
    unknown = sorted(
        column
        for column, value in row.items()
        if column not in _EVOLUTION_KEYS | _EVOLUTION_CONDITIONS
        and value not in ("", "0")
        and not (column in _FORM_COLUMNS and value in default_forms)
    )
    if unknown:
        raise ValueError(f"Conditions d'évolution non représentées dans la base : {unknown} ({dict(row)})")


def _conditions(row: dict[str, str], rules: EvolutionRules | None) -> tuple:
    """Conditions d'une évolution ; le bonheur des règles du moteur remplace celui de PokéAPI s'il est donné."""
    minimum_happiness = optional_int(row["minimum_happiness"])
    if minimum_happiness is not None and rules is not None:
        minimum_happiness = rules.happiness
    return (
        optional_int(row["minimum_level"]),
        optional_int(row["trigger_item_id"]),
        optional_int(row["held_item_id"]),
        minimum_happiness,
        row["time_of_day"] or None,
        optional_int(row["known_move_id"]),
        optional_int(row["trade_species_id"]),
        optional_int(row["minimum_beauty"]),
        optional_int(row["relative_physical_stats"]),
        _personality_chance(row),
    )


def _personality_chance(row: dict[str, str]) -> int | None:
    """Probabilité (%) d'une évolution que fixe la personnalité du Pokémon, None si elle n'en dépend pas."""
    expression, chance = row["condition_expression"], optional_int(row["percentage_chance"])
    if not expression and chance is None:
        return None
    if expression not in PERSONALITY_EXPRESSIONS or chance is None or not 0 < chance < 100:
        raise ValueError(f"Condition d'évolution inconnue : {expression!r} ({chance} %) pour {dict(row)}")
    return chance
