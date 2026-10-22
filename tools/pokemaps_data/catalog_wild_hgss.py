"""Provenance française et exigences des rencontres HGSS préparatoires."""

import re
from dataclasses import asdict
from pathlib import Path

from .catalog_maps_hgss import read_catalog
from .encounters_hgss import METHOD_NAMES, Distribution
from .obtainings_hgss import obtaining_catalog
from .pokeapi import PokeApi
from .pret_gen4_source import read_json, read_text
from .pret_hgss_maps import HgssMapRepo
from .pret_hgss_wild import TREE_SOURCE, WILD_SOURCE
from .sources import HGSS_PRET_COMMIT
from .special_wild_hgss import read_special_wild


def tree_catalog(root: Path) -> dict:
    source = read_text(root / "src/field/headbutt.c")
    lookups = {}
    pattern = r"sRareTreeLUT_(\w+)\[\]\[\d\] = \{(.*?)\};"
    for name, body in re.findall(pattern, source, re.DOTALL):
        rows = [re.findall(r"TREETYPE_(COMMON|RARE|NONE)", row) for row in re.findall(r"\{([^{}]+)\}", body)]
        if len(rows) < 10 or any(len(row) != (5 if name == "5Plus" else int(name)) for row in rows):
            raise ValueError(f"HGSS : table de classement des arbres invalide : {name}")
        lookups[name] = rows[:10]
    if set(lookups) != {"1", "2", "3", "4", "5Plus"}:
        raise ValueError("HGSS : tables de classement des arbres incomplètes")
    tables = read_json(root / TREE_SOURCE)["tables"]
    records = []
    for index, table in enumerate(tables):
        if not table["Trees"] and not table["SecretTrees"]:
            continue
        for group in (*table["Trees"], *table["SecretTrees"]):
            if not 1 <= len(group) <= 6 or any(set(p) != {"x", "y"} for p in group):
                raise ValueError(f"HGSS {index} : groupe de coordonnées d'arbre invalide")
        records.append(
            {"header": index, "native_map": table["Map"], "regular": table["Trees"], "secret": table["SecretTrees"]}
        )
    return {
        "source": TREE_SOURCE,
        "trees": records,
        "regular_tree_lookup": lookups,
        "rule_fr": "Dernier chiffre de l’identifiant complet du dresseur ; groupe modulo 5 dès cinq groupes. "
        "NONE signifie aucun combat. Les arbres particuliers ont leur propre table.",
    }


def encounter_catalog(
    root: Path, tables: tuple[Distribution, ...], trees: tuple[Distribution, ...], headers: dict, api: PokeApi
) -> dict:
    repo = HgssMapRepo(root, "heartgold")
    maps = read_catalog(repo)
    raw = read_json(root / WILD_SOURCE)["encounters"]
    names = api.names("pokemon_species_names", "pokemon_species_id")
    special = read_special_wild(root)
    obtainings = obtaining_catalog(root)
    return {
        "commit": HGSS_PRET_COMMIT,
        "versions": ["heartgold", "soulsilver"],
        "scope": "4A-4D",
        "radio_rate_effects": {
            "source": "src/field/encounter_check.c:FieldSystem_EncounterRateRoll",
            "march": {"first_roll_delta": 25, "label_fr": "Marche Pokémon"},
            "lullaby": {"first_roll_delta": -25, "label_fr": "Berceuse Pokémon"},
            "schedule_fr": "Marche le lundi et le vendredi ; Berceuse le mardi et le samedi. "
            "Le mercredi et le jeudi, les sons régionaux remplacent respectivement Marche et Berceuse "
            "après le National. Le dimanche, Lecteur GB si possédé, sinon Marche.",
            "note_fr": "Ces émissions gardent les espèces ordinaires. Elles modifient le premier seuil du moteur "
            "sur un octet non signé, avant son plafond à 100 ; ce seuil dépend aussi du déplacement, "
            "du terrain et des pas précédents. Aucun taux par pas n’est calculé.",
        },
        "methods_fr": dict(METHOD_NAMES),
        "conditions_fr": {
            "morn": "Matin",
            "day": "Jour",
            "nite": "Nuit",
            "off": "Radio désactivée",
            "hoenn": "Son de Hoenn — mercredi, Pokédex National",
            "sinnoh": "Son de Sinnoh — jeudi, Pokédex National",
            "swarm": "Essaim actif dans ce lieu — Pokédex National",
        },
        "species_fr": _catalog_species(names, tables + trees, special, obtainings),
        "banks": [
            {
                "bank": i,
                "native_map": row["map"],
                "headers": headers[i],
                "source": WILD_SOURCE,
                "status": "used" if headers[i] else "unreferenced",
            }
            for i, row in enumerate(raw)
        ],
        "technical_banks_fr": "ENCDATA_UNUSED_142 est déclaré sans membre JSON ; la banque inutilisée 90 "
        "est nommée 090 dans le JSON et ENCDATA_UNUSED_090 dans l’index natif.",
        "maps": [asdict(m) for m in maps if m.scope != "excluded"],
        "distributions": [asdict(t) for t in tables],
        "headbutt": [asdict(t) for t in trees],
        "headbutt_context": tree_catalog(root),
        "special_wild": special,
        "obtainings": obtainings,
        "probability_fr": "Probabilité conditionnelle à une rencontre, sans talent, objet, répulsif ni errant. "
        "rate est le paramètre brut du moteur, pas une probabilité par pas. "
        "Pour les arbres, rate reste nul au sens JSON (non applicable), sans taux inventé.",
        "excluded": ["Placement projeté et curation (4E)"],
    }


def _catalog_species(names: dict[int, str], tables: tuple[Distribution, ...], special: dict, obtainings: dict) -> dict:
    numbers = {s.species for table in tables for s in table.slots}
    numbers.update(n for row in obtainings["scripts"] for n in row["species"])
    numbers.update(row["given"] for row in obtainings["trades"])
    numbers.update(row["requested"] for row in obtainings["trades"] if row["requested"])
    for area in special["safari"]:
        for method in ("land", "surf", "oldrod", "goodrod", "superrod"):
            table = area[method]
            for period in ("morn", "day", "nite"):
                mons = table["mons"][period] + [row[period] for row in table["bonus_mons"]]
                numbers.update(special["species_ids"][m["species"]] for m in mons)
    numbers.update(s["species"] for row in special["contest"] for s in row["slots"])
    return {str(i): names[i] for i in sorted(numbers)}
