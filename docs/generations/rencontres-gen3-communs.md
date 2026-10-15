# Rencontres GBA : règles communes

`pret_gen3_wild.py` lit `wild_encounters.json` des trois dépôts pret épinglés.
`builder_wild_gen3.py` remplace les rencontres aléatoires PokéAPI par les tables du moteur.
Espèces répétées : probabilités additionnées, plages de niveaux réunies. Deux cartes rattachées
à la même zone doivent avoir des tables identiques. Dons, fixes, échanges et errants sont complétés séparément.

| Méthode | Probabilités des emplacements |
|---|---|
| Marche | 20/20/10/10/10/10/5/5/4/4/1/1 % |
| Surf, Éclate-Roc | 60/30/5/4/1 % |
| Canne | 70/30 % |
| Super Canne | 60/20/20 % |
| Méga Canne | 40/40/15/4/1 % |

Méthodes, nombres d’emplacements, niveaux, taux et probabilités sont validés ; toute structure
inconnue arrête la lecture. `map_areas.csv:version_group` permet un rattachement propre au groupe ;
`extra_areas.csv` conserve les zones absentes de PokéAPI. Les conditions Ligue, National, starter
et choix TV sont réunies entre méthodes au sol et dans l’eau.

`maps_terrain_gen3.py` détermine les cases depuis les comportements Hoenn et les attributs u32 des remakes.
Collisions, warps et objets occupés sont exclus. Les rochers viennent des objets Éclate-Roc et de leurs scripts.
Marée haute pour les rencontres aquatiques de Tréfonds ; layout de l’Île Mirage pour la marche du Chenal 130.

`compare_wild_gen3.py` écrit les écarts avec PokéAPI dans `encounter_comparison.json` :
Mirage, Métamo, salles inutilisées de la Grotte Origine, salle de Pierre et tables du Mont Braise notamment.
Les différences de granularité des zones restent explicites ; les sources du moteur font autorité.

Les commandes d’aperçu et l’éditeur sont décrits dans le [pipeline](../donnees/pipeline.md).
Pour les règles et limites de placement propres aux branches : [Hoenn](rencontres-hoenn.md),
[remakes](rencontres-remake-1g.md).
