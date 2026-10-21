"""Conditions françaises des tables HGSS, séparées de leur accessibilité locale."""

from .pret_hgss_pokemon import HgssPokemon

_CONDITIONS = {
    "EVO_LEVEL": "Monter au niveau {param}.",
    "EVO_LEVEL_ATK_GT_DEF": "Niveau {param}, Attaque supérieure à la Défense.",
    "EVO_LEVEL_ATK_EQ_DEF": "Niveau {param}, Attaque égale à la Défense.",
    "EVO_LEVEL_ATK_LT_DEF": "Niveau {param}, Attaque inférieure à la Défense.",
    "EVO_LEVEL_PID_HI": "Niveau {param}, branche déterminée par la personnalité (moitié haute).",
    "EVO_LEVEL_PID_LO": "Niveau {param}, branche déterminée par la personnalité (moitié basse).",
    "EVO_LEVEL_NINJASK": "Monter au niveau {param}.",
    "EVO_LEVEL_SHEDINJA": "Niveau {param}, place libre dans l'équipe et Poké Ball dans le sac.",
    "EVO_LEVEL_MALE": "Mâle, monter au niveau {param}.",
    "EVO_LEVEL_FEMALE": "Femelle, monter au niveau {param}.",
    "EVO_FRIENDSHIP": "Monter de niveau avec au moins 220 points de bonheur.",
    "EVO_FRIENDSHIP_DAY": "Monter de niveau de jour avec au moins 220 points de bonheur.",
    "EVO_FRIENDSHIP_NIGHT": "Monter de niveau de nuit avec au moins 220 points de bonheur.",
    "EVO_BEAUTY": "Monter de niveau avec une beauté d'au moins {param}, préparée dans un autre jeu.",
    "EVO_HAS_MOVE": "Monter de niveau en connaissant {param}.",
    "EVO_OTHER_PARTY_MON": "Monter de niveau avec {param} dans l'équipe.",
    "EVO_ITEM_DAY": "Monter de niveau de jour en tenant {param}.",
    "EVO_ITEM_NIGHT": "Monter de niveau de nuit en tenant {param}.",
    "EVO_STONE": "Utiliser {param}.",
    "EVO_STONE_MALE": "Mâle, utiliser {param}.",
    "EVO_STONE_FEMALE": "Femelle, utiliser {param}.",
    "EVO_TRADE": "Échanger le Pokémon.",
    "EVO_TRADE_ITEM": "Échanger le Pokémon en lui faisant tenir {param}.",
    "EVO_CORONET": "Monter de niveau dans un champ magnétique de Sinnoh, puis échanger vers HGSS.",
    "EVO_ETERNA": "Monter de niveau près de la Pierre Mousse de Sinnoh, puis échanger vers HGSS.",
    "EVO_ROUTE217": "Monter de niveau près de la Pierre Glace de Sinnoh, puis échanger vers HGSS.",
}


def evolution_rows(data: HgssPokemon, rules: dict, names: dict[str, str]) -> list[dict]:
    access = {method: row for row in rules["evolution_access"] for method in row["methods"]}
    result = []
    for row in data.evolutions:
        for evo in row["evos"]:
            method = evo["method"]
            if method not in _CONDITIONS:
                raise ValueError(f"HGSS {row['baseSpecies']} : méthode d'évolution inconnue : {method}")
            param = evo.get("param", 0)
            if isinstance(param, str) and param not in names:
                raise ValueError(f"HGSS {row['baseSpecies']} : paramètre d'évolution inconnu : {param}")
            result.append(
                dict(
                    species=row["baseSpecies"],
                    **evo,
                    access=access[method]["access"] if method in access else "local",
                    condition_fr=_CONDITIONS[method].format(param=names.get(param, param)),
                )
            )
    return result
