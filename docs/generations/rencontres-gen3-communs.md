# Génération 3 — Rencontres communes

Phase 4, partie « Communs », réalisée le 9 octobre 2026. Rubis/Saphir, Émeraude et Rouge Feu/Vert Feuille
restent des jeux préparatoires : aucune activation Android à cette étape.

## Lecture et assemblage

`pret_gen3_wild.py` lit `src/data/wild_encounters.json` des trois dépôts épinglés. Les suffixes sélectionnent
Rubis, Saphir, Rouge Feu ou Vert Feuille ; Émeraude n'en a pas. Les méthodes, groupes, nombres d'emplacements,
niveaux, taux et probabilités sont validés ; un format inconnu arrête la génération.

- Marche : 12 emplacements, 20/20/10/10/10/10/5/5/4/4/1/1 %.
- Surf et Éclate-Roc : 5 emplacements, 60/30/5/4/1 %.
- Canne : 70/30 % ; Super Canne : 60/20/20 % ; Méga Canne : 40/40/15/4/1 %.

`builder_wild_gen3.py` remplace les méthodes aléatoires de PokéAPI par ces tables. Les probabilités des espèces
répétées s'additionnent, leurs niveaux sont réunis ; les taux proviennent du moteur, y compris après une
correction éditoriale de zone. Deux cartes rattachées à la même zone doivent avoir des tables identiques.
Les dons, fixes, échanges et errants de PokéAPI sont conservés.

Les zones sont reliées aux cartes par `map_areas.csv`. La colonne facultative `version_group` remplace les
rattachements communs d'une carte pour un groupe : Émeraude renomme les anciennes zones est du Safari « Nord »
et « Sud », et utilise « Nord-est » et « Sud-est » pour l'extension. Rubis/Saphir conservent leurs noms d'origine.
Treize zones absentes sont ajoutées à `extra_areas.csv` : neuf tables Métamo d'Émeraude, la salle de Pierre
aux Chutes Météore et trois salles du Mont Braise avec leurs propres tables.

La Ligue conditionne l'extension Safari d'Émeraude. La Ligue et le Pokédex National conditionnent les rencontres
des Îles 4 à 7, du passage du Rubis et de la Grotte Azurée. Le choix TV rouge ou bleu d'Émeraude est conservé
même pour la valeur par défaut. Les conditions d'un errant sont réunies entre ses rencontres au sol et dans
l'eau : PokéAPI répartit ces conditions entre les deux. Les routes sont lues dans `sRoamerLocations` : 20 pour
chaque jeu de Hoenn, 25 pour les remakes ; Rubis/Saphir utilisent les numéros de cartes plutôt que des constantes.

## Terrains et aperçu PC

`maps_terrain_gen3.py` lit les comportements du moteur de Hoenn et les types de rencontre des attributs u32
des remakes. La pêche utilise l'eau surfable ; les rochers viennent des objets Éclate-Roc et de leurs scripts.
Les collisions, warps et objets occupés sont exclus des cases de placement. L'éditeur et la génération
valident les mêmes cases libres. Les marées partagent un en-tête sauvage mais changent de layout : les
méthodes aquatiques sont rattachées à la marée haute. La marche de la Route 130 est rattachée à l'Île Mirage.

```powershell
python tools/build_data.py --gen3-encounters-only --preview tools/build/preview/gen3-encounters
python tools/map_editor.py --assets tools/build/preview/gen3-encounters
```

L'aperçu contient les cinq versions, leurs cartes et sprites, rencontres, emplacements calculés et errants.
Il passe la validation complète de la base, y compris l'obtention des Pokédex par branche et les espèces
nécessitant un transfert. Les données de personnages et offres attendent la phase 5 ; cet aperçu a des calques
de personnages vides. L'éditeur propose Hoenn, sa carte sous-marine, Kanto et les Îles Sevii, et sait enregistrer
des emplacements pour les familles préparatoires. Les tables sous-marines utilisent provisoirement le terrain
aquatique commun : le terrain Plongée distinct et son affichage Android appartiennent à la branche Hoenn.

## Comparaison avec PokéAPI

`compare_wild_gen3.py` compare les espèces, plages de niveaux et probabilités des tables remplacées.
Chaque différence est écrite dans `encounter_comparison.json`, sans masquer les tables manquantes.
Les sources épinglées présentent **29 écarts** : Rubis 1, Saphir 1, Émeraude 15, Rouge Feu 6, Vert Feuille 6.

- Rubis/Saphir : la marche de la Route 130 appartient au layout variable de l'Île Mirage.
- Émeraude : même rattachement Mirage ; trois sous-sols inutilisés de la Grotte Origine encore listés par
  PokéAPI ; neuf tables Métamo explicites au lieu de sa seule zone générique ; salle de Pierre absente.
  Les tables Métamo B à I portent « Événement externe » et n'interviennent pas dans l'obtention.
- Remakes : PokéAPI place Éclate-Roc au sommet du Mont Braise sans table moteur correspondante, et omet les
  tables distinctes du troisième passage du sommet et des escaliers des deux premiers sous-sols du Rubis.

Les tests vérifient aussi une table identique aux deux sources (Route 101), les probabilités à 100 %, les
conditions, les routes errantes, les terrains et la base de l'éditeur. Les rencontres à probabilité NULL, négative ou supérieure à 100 %, les niveaux et quantités invalides font désormais échouer `validate.py`.

## Mesures et périmètre

Avec les sources et encodages en cache : génération validée en **14,2 s** ; aperçu de **56 010 876 octets**,
base de **4 022 272 octets** ; **1 463 cartes/zones**, **4 255 rencontres**, **9 328 emplacements calculés**.
Aucun fichier de l'aperçu ne dépasse 5 Mio. Les cartes versionnées restent à **31 544 227 octets** ; aucun asset
Android ni inventaire SHA-256 n'est modifié. APK debug déjà présent : **87 389 861 octets**, sans nouvelle
compilation ; paquets Git : **36 149 Kio**. Aucune dépendance ajoutée.

Les branches de phase 4 gardent les contenus particuliers, le placement éditorial et sa relecture visuelle.
Les séries de la Pyramide et du Reptile restent réservées à la branche Hoenn, conformément au plan.

La [branche Hoenn](rencontres-hoenn.md) est maintenant réalisée : terrain Plongée distinct, rencontres
particulières, grottes mobiles, séries de combat et emplacements relus. Ses corrections de rattachement
de Fondmer ajoutent des écarts de granularité au bilan historique des 29 tables ci-dessus.
