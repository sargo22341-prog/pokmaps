"""Consultation française de toutes les réserves et des 136 succès, sans serveur."""

from html import escape


def combat_review(data: dict) -> list[str]:
    battles = data["battles"]
    pieces = ['<h2 id="combat">Zone de Combat</h2>']
    for key in ("access_fr", "scope_fr"):
        pieces.append(f"<p>{escape(battles[key])}</p>")
    pieces.append(f"<p>{escape(battles['comparison']['rule_fr'])}</p>")
    for row in battles["facilities"]:
        pieces.append(f"<h3>{escape(row['name_fr'])}</h3><p>{escape(row['rules_fr'])}</p>")
        pieces.append(f"<p>{escape(row['reward_fr'])}</p>")
        for trainer in row["boss_trainers"]:
            pool = battles["trainers"][trainer]
            pieces.append(f"<p>Réserve du meneur {trainer} : {_links(pool)}</p>")
        if row["id"] == "tower":
            pieces.append(_series(battles["tower_ranges"]))
        elif row["id"] in ("castle", "arcade", "factory"):
            pieces.append(_series(battles["frontier"]["ranges"][row["id"]]))
    pieces.extend(_factory(battles["frontier"]["factory"]))
    pieces.extend(_rewards(battles["rewards"], data["item_names_fr"]))
    pieces.append("<details><summary>315 réserves de dresseurs</summary>")
    pieces.extend(f"<p>Dresseur {i} : {_links(pool)}</p>" for i, pool in enumerate(battles["trainers"]))
    pieces.append("</details><details><summary>950 configurations de combat</summary>")
    pieces.extend(_configuration(row, "set") for row in battles["sets"])
    pieces.append("</details><details><summary>Scène : dix rangs et 477 configurations</summary>")
    for i, bounds in enumerate(battles["frontier"]["hall"]["ranks"], 1):
        pieces.append(f"<p>Rang {i} : configurations {bounds[0]} à {bounds[1]}.</p>")
    pieces.extend(_configuration(row, "hall") for row in battles["frontier"]["hall"]["sets"])
    pieces.append('</details><h2 id="succes">Succès officiels partagés</h2>')
    pieces.append(f"<p>{escape(data['achievements']['scope_fr'])}</p>")
    for row in data["achievements"]["entries"]:
        warning = " · Manquable" if row["missable"] else ""
        pieces.append(
            f'<details id="ra-{row["identifier"]}"><summary>{escape(row["title"])} · '
            f"{row['points']} points{warning}</summary><p>{escape(row['description'])}</p>"
            f"<small>Identifiant officiel : {row['identifier']}</small></details>"
        )
    return pieces


def _links(pool: list[int]) -> str:
    return ", ".join(f'<a href="#set-{i}">{i}</a>' for i in pool) or "Sélection propre au moteur"


def _configuration(row: dict, prefix: str) -> str:
    return (
        f'<p id="{prefix}-{row["id"]}"><b>{row["id"]} · {escape(row["name"])}</b> : '
        f"{escape(', '.join(row['move_names']))} ; {escape(row['nature_name'])} ; "
        f"{escape(row['item_name']) or 'Sans objet'} ; forme {row['form']} ; "
        f"masque EV {row['evs']}.</p>"
    )


def _series(rows: list[dict]) -> str:
    return "".join(
        f"<p>Série {r['series']} : dresseurs {r['ordinary'][0]} à {r['ordinary'][1]} ; "
        f"dernier combat {r['last'][0]} à {r['last'][1]}, hors meneur.</p>"
        for r in rows
    )


def _factory(data: dict) -> list[str]:
    pieces = ["<h3>Réserves de l’Usine (bornes incluses)</h3>"]
    labels = {"level50": "Niveau 50", "open_player": "Libre : locations", "open_opponent": "Libre : adversaires"}
    for key, title in labels.items():
        pieces.append(f"<h4>{title}</h4>")
        for i, row in enumerate(data[key]):
            label = f"Série {i + 1}" if i < 8 else "Cardus Argent" if i == 8 else "Cardus Or"
            if key == "open_player" and i >= 8:
                label = f"Entrée native {i + 1} (non utilisée par le sélecteur de locations)"
            pieces.append(
                f"<p>{label} : configurations {row['min']} à {row['max']} ; IV {row['ivs']} ; "
                f"amélioration possible : {'oui' if row['upgrade'] else 'non'}.</p>"
            )
    return pieces


def _rewards(data: dict, names: dict[str, str]) -> list[str]:
    tower = data["tower"]
    pieces = [f"<h3>Récompenses de la Tour</h3><p>{escape(tower['rule_fr'])}</p>"]
    for key, title in (("ordinary", "Ordinaire"), ("link", "Liaison"), ("wifi_historical", "Wi-Fi historique")):
        pieces.append(f"<p>{title} : {', '.join(map(str, tower['tables'][key]))}.</p>")
    pieces.append(f"<h3>Lots du comptoir</h3><p>{escape(data['exchange']['rule_fr'])}</p>")
    for row in data["exchange"]["offers"]:
        pieces.append(
            f"<p>{escape(names[str(row['item'])])} × {row['quantity']} : "
            f"{row['cost']} Points Combat ; place vérifiée : {row['required_bag_space']}.</p>"
        )
    return pieces
