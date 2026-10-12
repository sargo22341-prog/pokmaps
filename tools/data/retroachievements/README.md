# Instantanés publics RetroAchievements

Export du 12 octobre 2026 : 20 ensembles principaux, 2 100 succès, générations 1 à 5.
Les fichiers `<identifiant>.json` conservent les titres et conditions officiels originaux,
points, ordre, type et date de modification ; `index.json` porte le nombre de succès et
l’empreinte SHA-256 de chaque fichier. Aucun résultat de joueur, nom de compte ni clé API.
Ces fichiers éditoriaux sont versionnés ; leur lecture et leurs tests ne nécessitent ni réseau ni clé.

L’ensemble 7212 rassemble HeartGold et SoulSilver. L’entrée SoulSilver 39076 est un ensemble
vide conservé comme tel, sans inventer de succès. La console Nintendo 3DS n’est pas présente
dans le catalogue des consoles actives utilisé lors de cet export ; les générations suivantes
ne sont donc pas disponibles par cette API. Les remakes GBA sont exportés séparément.
Les ensembles des générations 4 et 5 ne sont pas encore activés dans l’application.

`gen3_fr.csv` contient les 484 conditions GBA traduites et leurs titres français adaptés,
avec version PokéAPI, jeu RetroAchievements, succès officiel et chapitre du guide.
Les noms des Pokémon et lieux suivent les noms français ; les conditions, nombres et
restrictions officiels sont conservés. Les titres descriptifs remplacent certains jeux de mots.
Les fichiers JSON gardent les originaux pour toute relecture ultérieure.

| Jeu | Ensemble | Succès | Version PokéAPI |
|---|---:|---:|---:|
| Rubis | 790 | 49 | 7 |
| Saphir | 791 | 49 | 8 |
| Émeraude | 668 | 197 | 9 |
| Rouge Feu | 515 | 61 | 10 |
| Vert Feuille | 788 | 128 | 11 |

Les six anciens instantanés intégrés à l’application restent ceux du 8 octobre 2026.
L’archive plus récente conserve aussi leurs ensembles publics pour les futures mises à jour.
Les points nuls sont acceptés dans les archives des jeux futurs, conformément aux réponses officielles.

Mise à jour explicite, depuis la racine :

```powershell
python tools/export_retroachievements.py
```

Le programme demande la clé par une saisie masquée (`getpass`), ou lit la variable de processus
`RETROACHIEVEMENTS_API_KEY`. Il appelle uniquement `API_GetConsoleIDs`, `API_GetGameList` et
`API_GetGameExtended`, en lecture. Aucun nom d’utilisateur n’est nécessaire.
Les appels sont espacés, les réponses bornées en temps et taille, et HTTP 429 donne au plus trois tentatives.
Un échec arrête l’export ; l’inventaire n’est écrit qu’après tous les ensembles.
Toute mise à jour est à relire et valider avant d’être conservée.

Validation hors ligne : `cd tools; python -m pytest -q tests/test_retroachievements_exports.py`.
Ce test vérifie l’inventaire, les champs publics, les traductions et les définitions Android GBA.
La génération de `pokedex.db` et les builds Android n’appellent jamais cet exporteur.

Sources : [documentation API officielle](https://api-docs.retroachievements.org/),
[ensembles principaux](https://retroachievements.org/game/790).
