# Rencontres de Rouge Feu et Vert Feuille

Référence des rencontres distribuées et des exceptions de placement relues.

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
Les noms français des salles sont ceux du catalogue de cartes.

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

`map_spots.csv` conserve les placements relus dans la famille `firered-leafgreen`.
Chaque point est validé sur son terrain, avec au moins trois cases entre deux points.

Décision : préserver cet espacement et les rochers réels, plutôt que superposer les sprites ou
inventer des cases. **Quarante-neuf avertissements de capacité** restent visibles dans l'éditeur,
sans aucun terrain privé de point. Les Pokémon supplémentaires restent consultables dans la
liste du lieu ; l'application choisit un Pokémon par point disponible, comme pour les autres jeux.
Un test exige exactement ces manques et refuse toute nouvelle absence.

| Lieu et terrain | Points / marqueurs nécessaires | Motif |
|---|---|---|
| Céladopole, eau | 1 / 4 | Étang étroit |
| Grotte Azurée — 1er sous-sol, eau | 4 / 8 | Marqueurs allégés dans l'éditeur |
| Île 5, eau | 4 / 9 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 1, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 14, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 2, sol | 3 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 3, sol | 3 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 4, sol | 3 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 5, sol | 3 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 6, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 7, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 8, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte Perdue — Salle 9, sol | 4 / 5 | Marqueurs allégés dans l'éditeur |
| Île 4, eau | 4 / 8 | Marqueurs allégés dans l'éditeur |
| Grotte de Glace — Salle du fond, sol | 2 / 5 | Marqueurs allégés dans l'éditeur |
| Grotte de Glace — Salle du fond, eau | 5 / 9 | Marqueurs allégés dans l'éditeur |
| Grotte de Glace — Entrée, eau | 7 / 10 | Marqueurs allégés dans l'éditeur |
| Parmanie, eau | 1 / 7 | Marqueurs allégés dans l'éditeur |
| Mont Braise, escalier du Rubis B1F, rocher | 1 / 2 | Un seul rocher destructible |
| Mont Braise, escalier du Rubis B2F, rocher | 1 / 2 | Un seul rocher destructible |
| Île 1, eau | 2 / 8 | Marqueurs allégés dans l'éditeur |
| Plage Trésor, herbes | 4 / 6 | Marqueurs allégés dans l'éditeur |
| Bourg Palette, eau | 2 / 8 | Petit bassin au sud |
| Route 11, eau | 2 / 6 | Petite zone aquatique |
| Route 12, herbes | 1 / 4 | Marqueurs allégés dans l'éditeur |
| Route 13, herbes | 2 / 6 | Marqueurs allégés dans l'éditeur |
| Route 14, herbes | 1 / 6 | Parcelle allongée |
| Route 15, herbes | 4 / 6 | Marqueurs allégés dans l'éditeur |
| Route 16, herbes | 2 / 4 | Petite parcelle |
| Route 17, herbes | 2 / 5 | Marqueurs allégés dans l'éditeur |
| Route 18, herbes | 1 / 5 | Parcelle étroite |
| Route 22, eau | 1 / 7 | Petit bassin |
| Route 24, herbes | 3 / 7 | Bande entre rivière et chemin |
| Route 24, eau | 4 / 6 | Marqueurs allégés dans l'éditeur |
| Route 25, herbes | 2 / 7 | Petite parcelle au sud du chemin |
| Route 25, eau | 2 / 7 | Marqueurs allégés dans l'éditeur |
| Route 4, eau | 1 / 6 | Bande d'eau en bord de carte |
| Route 6, eau | 2 / 7 | Marqueurs allégés dans l'éditeur |
| Route 7, herbes | 3 / 4 | Marqueurs allégés dans l'éditeur |
| Parc Safari — Zone centrale, eau | 2 / 8 | Marqueurs allégés dans l'éditeur |
| Parc Safari — Zone est, eau | 4 / 8 | Marqueurs allégés dans l'éditeur |
| Parc Safari — Nord, eau | 3 / 8 | Marqueurs allégés dans l'éditeur |
| Parc Safari — Zone ouest, herbes | 5 / 9 | Marqueurs allégés dans l'éditeur |
| Parc Safari — Zone ouest, eau | 2 / 8 | Marqueurs allégés dans l'éditeur |
| Vallée Ruine, eau | 4 / 7 | Marqueurs allégés dans l'éditeur |
| Bois aux Baies, eau | 5 / 8 | Marqueurs allégés dans l'éditeur |
| Cap Falaise, herbes | 3 / 8 | Parcelles étroites de part et d'autre de la maison |
| Cap Falaise, eau | 3 / 8 | Marqueurs allégés dans l'éditeur |
| Jadielle, eau | 1 / 7 | Petit étang |
