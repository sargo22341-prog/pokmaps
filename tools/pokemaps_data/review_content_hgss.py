"""Page française de relecture hors ligne, liens locaux et données structurées."""

from html import escape
from pathlib import Path


def write_review(folder: Path, data: dict) -> None:
    pieces = [
        '<!doctype html><html lang="fr"><meta charset="utf-8"><title>Guides HGSS</title>',
        "<style>body{font:18px system-ui;max-width:1000px;margin:2rem auto;padding:1rem;line-height:1.6}",
        "details{border:1px solid #aaa;padding:1rem;margin:1rem 0}a{color:#075d94}small{display:block}</style>",
        "<h1>Guides et activités HeartGold / SoulSilver</h1>",
        '<p>Aperçu préparatoire hors ligne. <a href="content.json">Catalogue structuré complet</a>.</p>',
    ]
    for version, title in (("heartgold", "Or HeartGold"), ("soulsilver", "Argent SoulSilver")):
        pieces.append(f'<h2 id="{version}">{title}</h2>')
        for row in data["guides"]:
            if row["version"] == version:
                pieces.append(_guide(row, data["item_names_fr"]))
        pieces.append(_objectives(data, version))
    pieces.append('<h2 id="activites">Activités</h2>')
    for row in data["activities"]["guides"]:
        pieces.append(f'<details id="{escape(row["id"])}"><summary>{escape(row["title_fr"])}</summary>')
        pieces.append(f"<p>{escape(row['text_fr'])}</p><small>{escape(', '.join(row['sources']))}</small></details>")
    pieces.append('<h2 id="calendrier">Calendrier du Pokématos</h2>')
    for row in data["weekly"]:
        pieces.append(f"<p><b>{escape(row['title_fr'])}</b> : {escape(row['conditions_fr'])}</p>")
    for row in data["calendar"]["entries"]:
        pieces.append(
            f"<p><b>{escape(row['name_fr'])}</b> : {escape(row['weekday_fr'])}, "
            f"{escape(row['period_fr'])}. {escape(' ; '.join(row['conditions_fr']))}.</p>"
        )
    pieces.append("</html>")
    (folder / "index.html").write_text("\n".join(pieces) + "\n", encoding="utf-8")


def _guide(row: dict, item_names: dict[str, str]) -> str:
    places = ", ".join(p["name_fr"] for p in row["places"])
    actors = ", ".join(sorted({a["name_fr"] for a in row["actors"]}))
    items = ", ".join(sorted({_item_label(o, item_names) for o in row["items"]}))
    before = " · ".join(
        f'<a href="#{escape(row["version"])}-{escape(key)}">{escape(key)}</a>' for key in row["requires"]
    )
    return (
        f'<details id="{escape(row["version"])}-{escape(row["id"])}"><summary>{escape(row["title_fr"])}</summary>'
        f"<p>{escape(row['text_fr'])}</p><p>Étapes préalables : {before or 'Début'}</p>"
        f"<small>Lieux : {escape(places)}</small><small>Personnages : {escape(actors)}</small>"
        f"<small>Objets liés : {escape(items)}</small>"
        f"<small>Sources : {escape(', '.join(row['sources']))}</small></details>"
    )


def _item_label(row: dict, names: dict[str, str]) -> str:
    if row["values"]:
        item, quantity = row["values"]
        return f"{names[str(item)]} × {quantity}"
    if row["quantity_rule"]["kind"] == "matching_deposit":
        return "Balls de Fargas : une Ball par Noigrume confié"
    raise ValueError(f"HGSS : règle de lot inconnue : {row['id']}")


def _objectives(data: dict, version: str) -> str:
    pieces = ["<h3>Objectifs de capture</h3>"]
    for text in data["objective_rules"].values():
        if isinstance(text, str):
            pieces.append(f"<p>{escape(text)}</p>")
    names = data["names_fr"]
    for row in data["objectives"]:
        if row["version"] != version:
            continue
        starters = ", ".join(names[str(n)] for n in row["starters"].values())
        pieces.append(
            f"<details><summary>{escape(starters)} : {len(row['regional'])} régional, "
            f"{len(row['national'])} National</summary>"
        )
        for key, title in (("regional", "Régional"), ("national", "National"), ("excluded", "Exclusions")):
            pieces.append(f"<p>{title} : {escape(', '.join(names[str(n)] for n in row[key]))}</p>")
        pieces.append("</details>")
    return "\n".join(pieces)
