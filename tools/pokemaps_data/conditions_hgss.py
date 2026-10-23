"""Présentation française des conditions natives HGSS, sans suppression des prédicats."""


def condition_label(condition: dict) -> str:
    subject, operator, value = condition["subject"], condition["operator"], condition["value"]
    comparison = {
        "=": "égal à",
        "!=": "différent de",
        "<": "inférieur à",
        ">": "supérieur à",
        "<=": "au plus",
        ">=": "au moins",
    }[operator]
    names = {
        "player_starter": "Pokémon de départ",
        "player_gender": "Sexe du personnage",
        "game_version": "Version",
        "GetWeekday": "Jour",
        "GetTimeOfDay": "Période",
        "ScrCmd_522": "Heure",
        "GetPlayerFacing": "Direction du joueur",
        "GetMenuChoice": "Réponse au dialogue",
        "MenuExec": "Choix du menu",
        "random": "Résultat du tirage",
        "CheckBadge": "Possession du Badge",
        "HasItem": "Objet présent dans le sac",
        "GetItemQuantity": "Quantité dans le sac",
        "HasSpaceForItem": "Place disponible dans le sac",
        "CheckBattleWon": "Combat remporté",
        "CheckRegisteredPhoneNumber": "Numéro déjà enregistré",
        "GetPhoneBookRematch": "Rendez-vous de revanche actif",
        "GetPartyCount": "Pokémon dans l'équipe",
        "HasEnoughMoneyVar": "Argent suffisant",
        "HasEnoughMoneyImmediate": "Argent suffisant",
    }
    if subject == "player_starter":
        value = {152: "Germignon", 155: "Héricendre", 158: "Kaiminus"}.get(value, value)
    elif subject == "game_version":
        value = {7: "Or HeartGold", 8: "Argent SoulSilver"}.get(value, value)
    elif subject == "GetWeekday" and isinstance(value, int) and 0 <= value < 7:
        value = ("dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi")[value]
    elif subject == "var:16693":
        return f"Badges de Kanto : {comparison} {value}"
    if subject.startswith("flag:"):
        if subject == "flag:2404":
            return "Entrée au Panthéon effectuée" if value else "Avant l'entrée au Panthéon"
        return f"Condition de scénario {int(subject.split(':')[1]):#x} : {'active' if value else 'inactive'}"
    if subject.startswith("trainer_defeated:"):
        return f"Combat {subject.split(':')[1]} : {'déjà remporté' if value else 'à remporter'}"
    return f"{names.get(subject, 'État de scénario ' + subject)} : {comparison} {value}"


def translate_conditions(conditions: list[dict]) -> list[str]:
    return [condition_label(condition) for condition in conditions]
