"""Tables de consultation HGSS mises en paragraphes français avant le build Android."""

from .guide_resources_hgss import Article
from .placement_hgss import read_placement_json
from .sources import PREVIEW_DIR


def activity_articles(content: dict) -> list[Article]:
    data = content["activities"]
    result = _walker(content)
    result.extend(_safari(content))
    names = content["item_names_fr"]
    days = dict(
        zip(
            ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"),
            ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"),
            strict=True,
        )
    )
    for stock in data["pokeathlon"]["shops"]["daily"]:
        label = "après le National" if stock["national"] else "avant le National"
        lines = [f"{names[str(r['item'])]} × {r['quantity']} : {r['cost']} Points Athlète." for r in stock["items"]]
        result.append(
            Article(
                f"hgss-athlon-{stock['weekday']}-{stock['national']}",
                f"Prix du Pokéathlon — {days[stock['weekday']]} {label}",
                "Un exemplaire de chaque objet par jour.\n\n" + "\n\n".join(lines),
            )
        )
    return result


def _walker(content: dict) -> list[Article]:
    names, items = content["names_fr"], content["item_names_fr"]
    result = []
    for row in content["activities"]["pokewalker"]["courses"]:
        access = "Accès externe avec accessoire." if row["access"] != "accessory" else "Accessoire requis."
        intro = f"{access} {row['watts']} Watts cumulés ; "
        intro += "Pokédex National requis." if row["national"] else "sans Pokédex National."
        lines = [
            f"Groupe {r['group']} : [[pokemon:{r['species']}|{names[str(r['species'])]}]], "
            f"niveau {r['level']}, seuil {r['steps']} pas, poids de sélection {r['weight']}."
            for r in row["pokemon"]
        ]
        lines += [f"{items[str(r['item'])]} : seuil {r['steps']} pas, poids {r['weight']}." for r in row["items"]]
        text = intro + "\n\nLes poids ne sont pas des probabilités globales ; les groupes restent distincts.\n\n"
        result.append(
            Article(
                f"hgss-walker-{row['index']}", f"Pokéwalker — parcours {row['index'] + 1}", text + "\n\n".join(lines)
            )
        )
    return result


def _safari(content: dict) -> list[Article]:
    wild = read_placement_json(PREVIEW_DIR / "hgss-encounters/encounters.json")
    species = wild["special_wild"]["species_ids"]
    names = content["names_fr"]
    maps = {r["header"]: r["name_fr"] for r in wild["maps"]}
    kinds = {"PLAINS": "plaine", "FOREST": "forêt", "PEAK": "pic", "WATER": "eau"}
    result = []
    for area, habitat in enumerate(content["activities"]["safari"]):
        for method, label in (
            ("land", "Marche"),
            ("surf", "Surf"),
            ("oldrod", "Canne"),
            ("goodrod", "Super Canne"),
            ("superrod", "Méga Canne"),
        ):
            lines = []
            for period, title in (("morn", "Matin"), ("day", "Jour"), ("nite", "Nuit")):
                for index, mon in enumerate(habitat[method]["mons"][period], 1):
                    n = species[mon["species"]]
                    lines.append(
                        f"{title}, emplacement {index} sans blocs : [[pokemon:{n}|{names[str(n)]}]], "
                        f"niveau {mon['level']}, 10 %. "
                    )
                for index, bonus in enumerate(habitat[method]["bonus_mons"], 1):
                    mon = bonus[period]
                    n = species[mon["species"]]
                    needs = " et ".join(
                        f"{c['count']} points {kinds[c['object_type'].removeprefix('SAFARI_ZONE_OBJECT_TYPE_')]}"
                        for c in bonus["conditions"]
                    )
                    lines.append(
                        f"{title}, candidat {index} : [[pokemon:{n}|{names[str(n)]}]], "
                        f"niveau {mon['level']} ; {needs}. 10 % si retenu parmi les dix premiers admissibles."
                    )
            intro = "Trente objets au maximum par habitat. Les points dépendent de la maturation de l'habitat. "
            intro += "Les candidats admissibles remplacent les premiers emplacements dans l'ordre ci-dessous."
            result.append(
                Article(
                    f"hgss-safari-{area}-{method}", f"{maps[343 + area]} — {label}", intro + "\n\n" + "\n\n".join(lines)
                )
            )
    return result


def battle_articles(content: dict) -> list[Article]:
    data = content["battles"]
    result = [
        Article(
            "hgss-battle-" + r["id"],
            r["name_fr"],
            data["access_fr"] + "\n\n" + r["rules_fr"] + "\n\n" + r["reward_fr"],
            sources=tuple(r["sources"]),
        )
        for r in data["facilities"]
    ]
    for key, label, rows in (
        ("sets", "Configurations de combat", data["sets"]),
        ("hall", "Configurations de la Scène", data["frontier"]["hall"]["sets"]),
    ):
        for start in range(0, len(rows), 25):
            lines = [
                f"{r['id']} — {r['name']} : {', '.join(r['move_names'])} ; "
                f"{r['nature_name']} ; {r['item_name'] or 'sans objet'} ; forme {r['form']}."
                for r in rows[start : start + 25]
            ]
            result.append(
                Article(
                    f"hgss-battle-{key}-{start}",
                    f"{label} — {start + 1} à {min(start + 25, len(rows))}",
                    "Réserves possibles ; aucune équipe ni aucun tirage n'est prédit.\n\n" + "\n\n".join(lines),
                )
            )
    result.extend(_pools(data))
    items = content["item_names_fr"]
    lines = [
        f"{items[str(r['item'])]} × {r['quantity']} : {r['cost']} Points Combat."
        for r in data["rewards"]["exchange"]["offers"]
    ]
    result.append(Article("hgss-battle-rewards", "Lots de la Zone de Combat", "\n\n".join(lines)))
    return result


def _pools(data: dict) -> list[Article]:
    result = []
    for start in range(0, len(data["trainers"]), 25):
        lines = [
            f"Dresseur {index} : configurations {', '.join(map(str, pool)) or 'sélecteur propre au moteur'}."
            for index, pool in enumerate(data["trainers"][start : start + 25], start)
        ]
        result.append(
            Article(
                f"hgss-battle-trainers-{start}",
                f"Réserves de dresseurs — {start} à {start + len(lines) - 1}",
                "\n\n".join(lines),
            )
        )
    for key, label in (
        ("level50", "niveau 50"),
        ("open_player", "libre, locations"),
        ("open_opponent", "libre, adversaires"),
    ):
        lines = [
            f"Entrée {i + 1} : configurations {r['min']} à {r['max']} ; IV {r['ivs']}."
            for i, r in enumerate(data["frontier"]["factory"][key])
        ]
        result.append(Article("hgss-battle-factory-" + key, "Usine — " + label, "\n\n".join(lines)))
    return result
