# Remake 1G — Rencontres, terrains et emplacements

Phase 4, branche Rouge Feu/Vert Feuille, réalisée le 9 octobre 2026. Les jeux restent dans
`GAMES_IN_PROGRESS` : les données sont générées et validées dans l'aperçu PC. Leur sélection
dans l'application et l'interface des formes de Zarbi appartiennent à la phase 6.
Aucune dépendance ni modification du schéma Room.

## Ruines Tanoby

`pret_remake_encounters.py` lit `sUnownLetterSlots` dans `src/wild_encounter.c`, puis relie
les sept lignes aux chambres dans leur ordre réel de numéro de carte, comme `GenerateWildMon`.
Sept chambres contiguës, douze lettres par chambre et la couverture des 28 formes sont exigées ;
toute valeur, carte ou structure inconnue arrête la génération avec le nom de la source.

Les probabilités combinent les lettres C et les emplacements `land_mons` du JSON, sans diviser
la probabilité également entre les formes. Chaque rencontre de Zarbi garde 100 % au niveau 25 ;
sa note française `encounter.note_fr` conserve les formes, leurs probabilités et le déblocage.
L'énigme des sept rochers de la **Clé Tanoby**, à résoudre avec Force, est obligatoire
(`FLAG_SYS_UNLOCKED_TANOBY_RUINS`, script `SevenIsland_SevaultCanyon_TanobyKey`).

| Chambre pret | Formes et probabilités |
|---|---|
| Monean | A 99 %, ? 1 % |
| Liptoo | C 50 %, D 30 %, H 14 %, U 5 %, O 1 % |
| Weepth | N 60 %, S 30 %, I 8 %, E 2 % |
| Dilford | P 40 %, L 20 %, J 20 %, R 14 %, Q 6 % |
| Scufib | Y 40 %, T 20 %, G 25 %, F 13 %, K 2 % |
| Rixy | V 50 %, W 30 %, X 10 %, M 8 %, B 2 % |
| Viapois | Z 99 %, ! 1 % |

Les associations par salle sont conservées sans créer de Pokémon fictif dans la table des espèces.
Les noms français des salles restent ceux des cartes relues en phase 3.

## Progression et Grotte Métamo

- Les **Îles 1 à 3** sont accessibles avant la Ligue avec le Tri-Passe ; leurs rencontres ordinaires
  ne reçoivent aucune condition de Pokédex National. Exception : la parcelle à Insolourdo du
  **port de l'Île 3** devient accessible après le creusement du tunnel, déclenché par le National
  dans `ThreeIsland_DunsparceTunnel_OnTransition`.
- Les **Îles 4 à 7** exigent la Ligue et le Pokédex National. Les rencontres précisent aussi le
  **Passe Prisme** remis par Ciléo après la livraison du Rubis (`GiveCelioRuby`, `GiveRainbowPass`).
  Les tables du Chemin du Rubis au Mont Braise héritent des conditions de Ligue et de National.
- La **Grotte Métamo de l'Île 6** conserve ses neuf tables. A contient Nosferapti ; B à I portent
  « Événement externe » et restent exclues de l'obtention. La sélection du moteur vient de
  `VAR_ALTERING_CAVE_WILD_SET` ; aucune disponibilité normale de ces huit tables n'est inventée.
- La **Grotte Azurée**, y compris Mewtwo, exige la remise du Rubis **et du Saphir** à Ciléo.
  Cette étape retire `FLAG_HIDE_CERULEAN_CAVE_GUARD` et rétablit la liaison avec Hoenn.
  Cette condition supplémentaire est conservée dans la note de chaque rencontre.

Les drapeaux et variables d'offres et de personnages restent dans le périmètre de phase 5.
Les conditions des rencontres sont déjà conservées dans l'aperçu : identifiants PokéAPI pour
Ligue, National et starter, notes explicites pour Passe Prisme, Tanoby et la remise des deux pierres.

## Errants

Le lecteur vérifie le choix de `GetRoamerSpecies` et le niveau 50 de `CreateInitialRoamerMon`
dans `src/roamer.c`, pour chaque version. Les 25 routes possibles de Kanto sont lues dans
`sRoamerLocations` et rattachées à `roaming-kanto/area` ; aucune position fixe n'est inventée.

| Starter | Errant, dans les deux versions |
|---|---|
| Bulbizarre | Entei, niveau 50 |
| Salamèche | Suicune, niveau 50 |
| Carapuce | Raikou, niveau 50 |

`InitRoamer` est appelé après la remise du Saphir à Ciléo dans le Centre Pokémon de l'Île 1.
PokéAPI exige à tort une seconde Ligue : cette condition est retirée pour les seuls errants
des remakes, avec un test de régression. Ligue, National, starter et remise des pierres sont conservés.
Le moteur tente l'errant à pied **et pendant Surf** (`TryStandardWildEncounter`) : les rencontres
`roaming-water`, absentes de PokéAPI pour ces jeux, sont ajoutées avec les mêmes conditions.

## Terrains et emplacements

Les attributs u32 fournissent `TILE_ENCOUNTER_LAND` et `TILE_ENCOUNTER_WATER` (bits 24 à 26).
Le comportement ne décide pas de l'existence d'une rencontre terrestre ou de Surf ; il distingue
ensuite les herbes du sol et les cases où l'on peut pêcher. Les herbes de la Piste Cyclable
(`MB_CYCLING_ROAD_PULL_DOWN_GRASS`, 0xD1) sont corrigées : elles ne sont plus classées comme sol.
Les rochers d'Éclate-Roc viennent des objets et de leur script. Collisions, objets occupés et
entrées sont exclus des points libres.

`map_spots.csv` conserve **3 294 points**, sur **168 terrains**, couvrant les **124 lieux**
proposés dans l'éditeur. Les points sont sélectionnés puis relus sur huit planches PC avec les
sprites à l'échelle de l'application et les entrées. Ils appartiennent à la famille
`firered-leafgreen`, sans reprise des points de Rouge/Bleu/Jaune ; les deux remakes partagent le plan.
Chaque point est validé sur son terrain, avec au moins trois cases entre deux points d'un terrain.

Décision : préserver cet espacement et les rochers réels, plutôt que superposer les sprites ou
inventer des cases. **Quatorze avertissements de capacité** restent visibles dans l'éditeur,
sans aucun terrain privé de point. Les Pokémon supplémentaires restent consultables dans la
liste du lieu ; l'application choisit un Pokémon par point disponible, comme pour les autres jeux.
Un test exige exactement ces manques et refuse toute nouvelle absence.

| Lieu et terrain | Points / marqueurs nécessaires | Motif |
|---|---|---|
| Bourg Palette, eau | 2 / 8 | Petit bassin au sud |
| Céladopole, eau | 2 / 4 | Étang étroit |
| Jadielle, eau | 4 / 7 | Petit étang |
| Cap Falaise, herbes | 5 / 8 | Parcelles étroites de part et d'autre de la maison |
| Mont Braise, escalier du Rubis B1F, rocher | 1 / 2 | Un seul rocher destructible |
| Mont Braise, escalier du Rubis B2F, rocher | 1 / 2 | Un seul rocher destructible |
| Route 4, eau | 4 / 6 | Bande d'eau en bord de carte |
| Route 11, eau | 5 / 6 | Petite zone aquatique |
| Route 14, herbes | 4 / 6 | Parcelle allongée |
| Route 16, herbes | 3 / 4 | Petite parcelle |
| Route 18, herbes | 4 / 5 | Parcelle étroite |
| Route 22, eau | 4 / 7 | Petit bassin |
| Route 24, herbes | 5 / 7 | Bande entre rivière et chemin |
| Route 25, herbes | 3 / 7 | Petite parcelle au sud du chemin |

## Reproduction et contrôles

```powershell
python tools/build_data.py --gen3-encounters-only --preview tools/build/preview/gen3-encounters
python tools/map_editor.py --assets tools/build/preview/gen3-encounters
```

L'aperçu des cinq versions GBA est régénéré et validé en **16,5 s** avec cache :
**4 294 rencontres**, **9 552 emplacements**, **1 463 cartes/zones**, base de **4 108 288 octets**.
L'aperçu occupe **56 196 630 octets**, hors images locales de relecture.
Cartes versionnées inchangées : **31 630 579 octets**, dont **7 327 137 octets** pour les remakes.
APK debug vérifié : **87 390 017 octets**. Aucun asset final ne dépasse 5 Mio.
Git : **36 149 Kio** de paquets et **917 Kio** d'objets locaux avant commit.

Validation des assets et SHA-256, Ruff et formatage, limites de 600 lignes par fichier et
60 lignes par fonction, relecture du diff et des emplacements : réussis.
Suite Python ordinaire : **282 tests réussis** ; pipeline complet : **152 tests réussis**.
Les contrôles Android `ktlintCheck`, `checkNoGoogleServices`, `lintDebug`, `testDebugUnitTest`
et `assembleDebug` passent ; les tâches de compilation et tests Android étaient à jour,
le code et les assets Android étant inchangés.

Incidents corrigés : accès refusés au cache pytest et au verrou Gradle dans le bac à sable,
puis contrôles exécutés avec les permissions nécessaires ; commande Ruff utilisée via `python -m ruff` ;
nettoyage du dossier temporaire `tools/tools` contenant cache et sorties de tests non versionnés.
Un premier rendu a lu une tuile pendant sa recopie par la génération : la relecture est relancée
après la fin de la génération et réussit. Aucun échec de test métier.
La dépréciation AGP `Configuration.setVisible(boolean)`, déjà documentée dans le README,
reste affichée ; aucun avertissement Kotlin, Lint, ktlint, Ruff ou pytest restant.
Git signale les conversions LF/CRLF de sa configuration ; `git diff --check` passe.
Pas d'essai sur téléphone : les remakes ne sont pas encore sélectionnables avant la phase 6.
