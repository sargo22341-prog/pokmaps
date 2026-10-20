# Archives RetroAchievements

Instantanés publics des ensembles principaux des générations 1 à 5, exportés le 12 octobre 2026.
`<identifiant>.json` conserve titres, conditions, points, ordre, type et date de modification ;
`index.json` inventorie fichiers, nombres et SHA-256. Aucun résultat de joueur, nom de compte ni clé API.
La génération 4 est activée ; la génération 5 reste archivée.

| Traductions | Jeux distribués | Ressources produites |
|---|---|---|
| `gen12_fr.csv` | Rouge, Bleu, Jaune, Or, Argent, Cristal | `strings_achievements_<version>.xml` |
| `gen3_fr.csv` | Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille | Même format |
| `gen4_fr.csv` | Diamant, Perle, Platine | Même format, ensembles 9852, 25369, 11732 |

Les CSV associent version PokéAPI, ensemble officiel, succès et chapitre. Les titres français peuvent
être adaptés ; conditions, nombres et restrictions restent ceux des originaux archivés.
L’ensemble 7212 regroupe HeartGold/SoulSilver ; 39076 est vide et reste vide. Les points nuls des jeux futurs
sont acceptés. Les archives n’ont pas de source 3DS dans le catalogue des consoles utilisé lors de l’export.

## Mettre à jour

Depuis la racine :

```powershell
python tools/export_retroachievements.py
python tools/build_data.py --achievement-resources-only
cd tools
python -m pytest -q tests/test_retroachievements_exports.py
```

L’exporteur demande la clé par saisie masquée ou lit `RETROACHIEVEMENTS_API_KEY` dans le processus.
Il appelle uniquement `API_GetConsoleIDs`, `API_GetGameList` et `API_GetGameExtended`, en lecture,
sans nom d’utilisateur. Appels espacés, réponses bornées, trois tentatives maximum pour HTTP 429.
Un échec arrête l’export ; l’inventaire est écrit après tous les ensembles. Relire avant de conserver la mise à jour.

JSON UTF-8, fins de ligne LF : empreintes identiques sur Windows et Linux. La génération des ressources
et ses tests utilisent les archives locales sans clé ni réseau ; versionner les sorties Android sans les éditer.
La génération de la base et les builds Android n’appellent jamais l’exporteur authentifié.
La connexion facultative d’un joueur est distincte : voir les [Réglages](../../../docs/fonctionnalites/reglages.md).

Référence externe : [documentation API officielle](https://api-docs.retroachievements.org/).
