# Hoenn — Rencontres, terrains et emplacements

Phase 4, branche Hoenn, réalisée le 9 octobre 2026 pour Rubis, Saphir et Émeraude.
Les jeux restent préparatoires : leurs rencontres se consultent dans l'aperçu PC ; leur activation
Android appartient à la phase 6. Aucune dépendance ajoutée.

## Rencontres et conditions

- **Plongée** : seules les cartes sous les Routes 124 et 126 ont des tables `water_mons`, traduites
  en méthode `seaweed`. Rubis/Saphir les nomment `Underwater1` et `Underwater2`. Les Pokémon se
  placent dans les algues autorisées par le moteur, sur le terrain distinct `underwater`.
- **Barpau** : niveaux 20 à 25, 50 % avec toute canne sur les cases choisies par le moteur. Les six
  tirages dépendent de la sauvegarde et de la phrase à la mode de Myokara, et peuvent coïncider.
  La rencontre reste dans la liste de la Route 119 avec une note explicite : ses coordonnées
  sont impossibles à placer sur une carte fixe.
- **Grotte Métamo** : l'entrée de la Route 103 s'ouvre après la Ligue
  (`Route103_OnLoad`, `FLAG_SYS_GAME_CLEAR`). Les neuf tables héritent de cette condition.
  A donne Nosferapti ; B à I portent « Événement externe » et ne comptent pas dans l'obtention.
  Leurs noms français, dont certains accents étaient abîmés, sont corrigés.
- **Parc Safari** : les zones ordinaires restent accessibles sans condition de Ligue.
  L'extension nord-est/sud-est d'Émeraude exige la Ligue ; Rubis/Saphir gardent leurs quatre zones.
- **Kecleon** : les rencontres fixes des Routes 119 et 120 indiquent l'usage du Devon Scope,
  au niveau 30. Les positions des personnages appartiennent aux données de phase 5.
- **Simularbre** : niveau 40, Wailmerrosoir à la Zone de Combat, après la Ligue.
- **Errants** : Latios dans Rubis, Latias dans Saphir ; dans Émeraude, choix Rouge pour Latias,
  Bleu pour Latios. Tous sont au niveau 40, après la Ligue. Les conditions sont communes aux
  méthodes au sol et dans l'eau. Les vingt routes possibles viennent de `sRoamerLocations`.

Les épidémies TV facultatives ne sont pas retenues dans cette phase. L'aperçu décrit les tables
permanentes et les rencontres particulières ci-dessus. Il ne simule pas les informations d'une
sauvegarde ni les épidémies reçues par mélange de données.

## Grottes à entrée mobile

`pret_hoenn_caves.py` lit les deux tables `sAbnormalWeatherMapNumbers` de `field_specials.c`.
Elles doivent être identiques et contenir seize positions, soit deux positions par route.
Les grottes sont reliées aux routes possibles dans la base, comme les errants, en conservant
leur salle finale. Aucun marqueur d'entrée permanent n'est inventé.

| Rencontre d'Émeraude | Routes possibles | Condition |
|---|---|---|
| Groudon, Grotte Terra, niveau 70 | 114, 115, 116, 118 | Après la Ligue ; scientifique de l'Institut Météo |
| Kyogre, Grotte Marine, niveau 70 | 105, 125, 127, 129 | Après la Ligue ; scientifique de l'Institut Météo |

Les notes indiquent ces routes et le scientifique. Rubis/Saphir conservent Groudon/Kyogre à la
Grotte Origine, niveau 45 ; aucune règle des grottes mobiles ne leur est appliquée.

## Terrains et rattachements

Herbes hautes, longues et cendrées, sable du désert, sol des grottes et eau suivent les
attributs de comportement de chaque moteur Hoenn. Collisions bloquantes, objets occupés et warps
sont exclus du placement. Éclate-Roc utilise les objets rochers et leurs scripts.
`underwater` est reconnu par `SpotKind`, les terrains Python, la validation, le CSV et l'éditeur,
qui l'affiche comme « Algues sous-marines (Plongée) ».

La relecture a corrigé le rattachement trop large de la Caverne Fondmer : l'entrée ne propose
que les méthodes aquatiques, les salles sèches seulement la marche, et les salles inondées les deux.
La salle finale n'a pas de table sauvage et n'apparaît plus dans l'éditeur des rencontres.
Trois zones éditoriales remplacent la zone PokéAPI globale pour ces tables.

## Installations de combat

`pret_hoenn_facilities.py` exporte les vraies espèces et attaques des tables C dans l'asset
`maps/emerald/facility_encounters.json`, inclus dans l'inventaire SHA-256 et copié dans l'aperçu.
Il liste vingt séries de Pyramide et quatre de Reptile, chacune en niveau 50 et en niveau ouvert :
**48 séries et 344 emplacements**. Le catalogue est validé et comparé aux sources par les tests.

Les espèces JSON de la Pyramide servent d'indices ; les en-têtes `battle_pyramid_*_wild_mons.h`
fournissent les vraies espèces. Les niveaux JSON à 5 sont des valeurs techniques. Le catalogue
conserve les paramètres réels et explique les formules : niveau ± 5 à la Pyramide, réduction
du niveau de référence en mode ouvert ; 50 moins le paramètre au Reptile, ou niveau maximal
de l'équipe diminué du paramètre avec minimum 60 en mode ouvert. La Pyramide répète ses vingt
passages de sept étages ; le Reptile change de série aux seuils de 20, 40 et 60 passages.

Ces Pokémon ne sont pas capturables. Le catalogue porte explicitement la mention « Pokémon
non capturables ; assemblages aléatoires non simulés ». Ils ne sont pas introduits dans les
tables d'obtention ni sur des emplacements sauvages fixes.

## Emplacements et décisions de place

`map_spots.csv` conserve **4 523 points** sur **152 terrains distincts** : 80 retouches communes,
49 propres à Rubis/Saphir et 67 propres à Émeraude, via `version_group`. Tous les points sont
validés dans les cases libres de leur version. La relecture PC couvre les 101 lieux initialement
proposés pour Rubis/Saphir et les 117 pour Émeraude avec les sprites de l'éditeur ; la salle
finale de Fondmer est ensuite retirée des deux listes.

Décision : garder l'espacement d'au moins trois cases et les petits terrains lisibles. Les six
terrains ci-dessous conservent un avertissement de capacité ; aucune absence d'emplacement
n'est admise. Un Pokémon tiré au hasard occupe chaque point disponible, les autres restent
dans la liste du lieu, conformément au comportement de `WildPlacement`.

| Terrain | Jeux | Points / marqueurs nécessaires | Motif |
|---|---|---|---|
| Épave, couloir sous-marin, eau | Rubis/Saphir | 1 / 5 | Petite poche d'eau à l'entrée |
| Épave, salles du premier sous-sol, eau | Rubis/Saphir | 1 / 5 | Petit bassin central |
| Myokara, eau | Rubis/Saphir et Émeraude | 5 / 6 | Bande d'eau entre plage et bord de carte |
| Site Météore, sous-sol 1 salle 2, eau | Rubis/Saphir | 5 / 6 | Bassin étroit entouré de falaises |
| Route 102, eau | Rubis/Saphir et Émeraude | 3 / 5 | Petit étang isolé |
| Route 115, herbes | Rubis/Saphir et Émeraude | 2 / 5 | Petites parcelles hors du chemin |

Cela représente neuf avertissements au total : six en Rubis/Saphir, trois en Émeraude. Ils restent visibles dans
l'éditeur ; aucun n'est supprimé ou rendu silencieux.

## Reproduction et mesures

```powershell
python tools/build_data.py --hoenn-maps-only
python tools/build_data.py --gen3-encounters-only --preview tools/build/preview/gen3-encounters
python tools/map_editor.py --assets tools/build/preview/gen3-encounters
```

La première commande régénère les cartes, le catalogue des installations et l'inventaire.
La seconde applique les retouches au seul aperçu. Les personnages, offres et positions des
Pokémon fixes suivent le périmètre de phase 5.

Avec cache : cartes Hoenn régénérées en **63,5 s** ; aperçu mesuré pendant les contrôles parallèles
en **44,7 s**, **56 110 614 octets**, base **4 022 272 octets**, **1 463 cartes/zones**,
**4 288 rencontres**, **9 328 emplacements** pour les cinq versions GBA. Les images de relecture
locales sont exclues de cette taille et de Git.

Cartes versionnées : **31 630 579 octets**, dont **86 352 octets** pour le nouveau catalogue.
Aucun asset ne dépasse 5 Mio. APK debug recompilé : **87 390 017 octets**. Paquets Git :
**36 149 Kio**, objets locaux non empaquetés : **110 Kio** avant commit.

## Contrôles et incidents

Génération explicite des cartes Hoenn et de l'aperçu, validation des assets et SHA-256, Ruff,
contrôle des tailles de sources, relecture du diff et des cartes : réussis. Suite Python ordinaire :
**269 tests réussis** ; pipeline complet : **146 tests réussis** ; dernières régressions Hoenn :
**15 tests réussis**. Android : `ktlintCheck`, `checkNoGoogleServices`, `lintDebug`,
`testDebugUnitTest` (dont `PokedexSchemaTest`) et `assembleDebug` réussis.

Les premiers essais ont rencontré les permissions de cache/temporaire du bac à sable Windows :
les contrôles ont ensuite été exécutés avec les permissions nécessaires. Deux tests existants
supposaient toutes les familles actives ou cinq terrains ; leurs attentes sont adaptées au périmètre
des bases et au terrain sous-marin vide en génération 2. Une attente nouvelle supposait à tort trois
cartes sous-marines sauvages ; les sources en montrent deux. Le lecteur des séries de combat a aussi
été corrigé pour accepter les talents fixés aux indices 0/1, en plus de `ABILITY_RANDOM`.

Gradle affiche encore la dépréciation `Configuration.setVisible(boolean)` d'AGP documentée dans
le README. Git signale les conversions LF/CRLF prévues par sa configuration ; le diff passe son
contrôle de whitespace. Aucun avertissement Kotlin, Lint, ktlint, Ruff ou pytest restant.
Pas d'essai sur téléphone : Hoenn n'est pas encore sélectionnable dans l'application, conformément
au périmètre de phase 4.
