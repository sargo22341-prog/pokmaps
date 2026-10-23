"""Ressources françaises HGSS : textes et métadonnées de guides, sans génération de code."""

import json
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from .maps_layout import identifier
from .placement_hgss import read_placement_json
from .sources import HGSS_PRET_COMMIT, PREVIEW_DIR


@dataclass(frozen=True)
class Article:
    key: str
    title: str
    text: str
    versions: tuple[int, ...] = (15, 16)
    category: str = "SIDE_QUEST"
    related: tuple[str, ...] = ()
    captures: tuple[int, ...] = ()
    sources: tuple[str, ...] = ()


def articles(content: dict) -> list[Article]:
    maps = read_placement_json(PREVIEW_DIR / "hgss-maps/atlas/catalog.json")
    places = {r["header"]: identifier(r["const"]) for r in maps["maps"]}
    result = []
    for row in content["guides"]:
        links = ", ".join(f"[[place:{places[p['header']]}|{p['name_fr']}]]" for p in row["places"])
        result.append(
            Article(
                "hgss-" + row["id"],
                row["title_fr"],
                row["text_fr"] + "\n\nLieux : " + links,
                ({"heartgold": 15, "soulsilver": 16}[row["version"]],),
                "WALKTHROUGH" if row["category"] in {"johto", "kanto", "postgame"} else "SIDE_QUEST",
                tuple("hgss-" + key for key in row["requires"]),
                sources=tuple(row["sources"]),
            )
        )
    result.extend(
        Article("hgss-activity-" + r["id"], r["title_fr"], r["text_fr"], sources=tuple(r["sources"]))
        for r in content["activities"]["guides"]
    )
    result.extend(_objectives(content))
    result.append(_calendar(content))
    from .guide_tables_hgss import activity_articles, battle_articles

    result.extend(activity_articles(content))
    result.extend(battle_articles(content))
    from .guide_scenes_hgss import scene_articles

    result.extend(scene_articles(content))
    result.extend(_tools())
    for version in (15, 16):
        selected = [a for a in result if version in a.versions]
        if len(selected) + 136 > 500 or len({a.key for a in selected}) != len(selected):
            raise ValueError(f"HGSS : guides trop nombreux ou répétés pour la version {version}")
        known = {a.key for a in selected}
        if any(set(a.related) - known for a in selected):
            raise ValueError(f"HGSS : lien entre guides inconnu pour la version {version}")
    if any(not a.title or not a.text or len(a.text) > 30_000 for a in result):
        raise ValueError("HGSS : titre ou contenu de guide invalide")
    return result


def _objectives(content: dict) -> list[Article]:
    names = content["names_fr"]
    result = []
    for row in content["objectives"]:
        starters = ", ".join(names[str(n)] for n in row["starters"].values())
        for key, label in (("regional", "régional"), ("national", "National")):
            text = content["objective_rules"]["scope_fr"] + "\n\n" + content["objective_rules"]["choices_fr"]
            text += "\n\nPokémon accessibles : " + ", ".join(f"[[pokemon:{n}|{names[str(n)]}]]" for n in row[key])
            text += "\n\nExclusions :\n" + "\n".join(
                f"{names[str(r['species'])]} : {r['reason_fr']}" for r in row["exclusions"]
            )
            result.append(
                Article(
                    "hgss-goal-" + row["id"] + "-" + key,
                    f"Objectif {label} — {starters}",
                    text,
                    ({"heartgold": 15, "soulsilver": 16}[row["version"]],),
                    captures=tuple(row[key]),
                )
            )
    return result


def _calendar(content: dict) -> Article:
    lines = [r["title_fr"] + " : " + r["conditions_fr"] for r in content["weekly"]]
    lines += [
        f"{r['name_fr']} : {r['weekday_fr']}, {r['period_fr']}. " + " ; ".join(r["conditions_fr"])
        for r in content["calendar"]["entries"]
    ]
    return Article(
        "hgss-weekly-calendar", "Rendez-vous et revanches du Pokématos", "\n\n".join(lines), category="CALENDAR"
    )


def build_resources(content: dict, output: Path) -> None:
    rows = articles(content)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<!-- Les textes par défaut sont français : utiliser le dictionnaire français de Lint. -->",
        '<resources xmlns:tools="http://schemas.android.com/tools" tools:locale="fr">',
    ]
    texts, references = _text_resources(rows)
    lines.extend(texts)
    metadata = []
    for row in rows:
        metadata.append(
            json.dumps(
                dict(
                    id=row.key,
                    versions=row.versions,
                    category=row.category,
                    related=row.related,
                    captures=row.captures,
                    sources=row.sources,
                ),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    for suffix in ("title", "text"):
        lines.append(f'    <array name="hgss_guide_{suffix}s">')
        lines.extend(f"        <item>@string/{name}</item>" for name in references[suffix])
        lines.append("    </array>")
    lines.append('    <string-array name="hgss_guide_metadata" translatable="false">')
    lines.extend(
        "        <item>" + escape(value).replace('"', '\\"').replace("'", "\\'") + "</item>" for value in metadata
    )
    lines.extend(["    </string-array>", "</resources>"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "strings_guides_hgss.xml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _text_resources(rows: list[Article]) -> tuple[list[str], dict[str, list[str]]]:
    lines: list[str] = []
    # Les noms français communs des installations utilisent les ressources déjà compilées.
    names = {
        "Tour de Combat": "sinnoh_tower",
        "Usine de Combat": "sinnoh_factory",
        "Castel de Combat": "sinnoh_castle",
        "Arcade de Combat": "sinnoh_arcade",
    }
    references: dict[str, list[str]] = {"title": [], "text": []}
    for index, row in enumerate(rows):
        for suffix, text in (("title", row.title), ("text", row.text)):
            normalized = text.replace("'", "’")
            if normalized not in names:
                name = f"hgss_guide_{index}_{suffix}"
                names[normalized] = name
                value = escape(normalized).replace('"', '\\"').replace("\n", "\\n")
                lines.append(f'    <string name="{name}" formatted="false">{value}</string>')
            references[suffix].append(names[normalized])
    return lines, references


SOURCE = f"https://github.com/pret/pokeheartgold/blob/{HGSS_PRET_COMMIT}/"


def _tools() -> list[Article]:
    return [
        Article(
            "breeding",
            "Reproduction dans HeartGold et SoulSilver",
            "La Pension de la Route 34 conserve deux Pokémon. Le type d'œuf dépend des parents et des encens. "
            "Les objets Pouvoir imposent la transmission d'un IV ; deux porteurs ne garantissent pas deux IV. "
            "La Pierre Stase et les langues des parents suivent les règles HGSS. "
            "L'outil détaille les possibilités sans prédire les tirages.",
            category="TIP",
            sources=("src/get_egg.c",),
        ),
        Article(
            "friendship",
            "Bonheur dans HeartGold et SoulSilver",
            "Les gains et pertes dépendent du bonheur courant. Luxe Ball, lieu de réception de l'œuf et "
            "Grelot Zen interviennent dans cet ordre. Les coiffeurs et Nina ont leurs résultats propres. "
            "L'évolution par bonheur demande 220 points ; l'outil n'observe aucune sauvegarde.",
            category="TIP",
            sources=("src/pokemon.c", "src/use_item_on_mon.c"),
        ),
        Article(
            "hgss-roamers",
            "Retrouver les Pokémon errants",
            "Après la Tour Cendrée, Raikou et Entei parcourent Johto au niveau 40. "
            "Après la quête de la Copieuse et la rencontre avec Pierre à Carmin sur Mer, Latias dans Or HeartGold "
            "ou Latios dans Argent SoulSilver parcourt Kanto au niveau 35. "
            "Noter ici la dernière route observée ; aucune position future n'est prédite. "
            "Suicune suit un parcours de scénario et reste un combat fixe.",
            sources=("src/field_roamer.c",),
        ),
    ]
