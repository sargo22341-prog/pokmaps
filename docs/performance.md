# Performances : référence sur téléphone

Référence mesurée le 13 octobre 2026, avant puis après quatre optimisations du fil principal :
transformations hors du fil principal, mise à jour incrémentale des marqueurs de la carte, index du catalogue,
transition des guides.
Ces chiffres valent pour l'appareil et la build décrits ici ; ce ne sont pas des budgets universels.

## Conditions

| Élément | Valeur |
|---|---|
| Appareil | Pixel 6 Pro, GrapheneOS (Android 17, build `CP3A.261005.002.A1`), écran réglé à 60 Hz |
| Budget d'une frame | 16,7 ms |
| Build | release minifiée (R8, réduction des ressources), `profileable`, paquet `org.opensources.pokmaps.perf` |
| Compilation ART | `speed` à l'installation |
| Température | statut thermique 0 du début à la fin, batterie entre 23,6 et 25,9 °C, sur USB |
| Sprites animés | réglage par défaut (deux endroits sur sept), sauf mention contraire |

La build de mesure ne modifie pas le dépôt : un script d'initialisation Gradle local applique, dans
`androidComponents.finalizeDsl`, le suffixe `.perf`, `profileable = true` et la signature debug à la variante
release, puis `.\gradlew.bat --init-script <script> assembleRelease`. Le paquet distinct laisse intactes
la build debug et ses données. Les identifiants R8 se lisent avec `app/build/outputs/mapping/release/mapping.txt`.

GrapheneOS refuse la source `linux.ftrace` de Perfetto : ni ordonnancement, ni sections atrace. Les mesures
utilisent donc des outils qui fonctionnent sans elle :

- `dumpsys gfxinfo <paquet> reset`, puis `dumpsys gfxinfo <paquet> [framestats]` : frames et percentiles ;
- `/proc/<pid>/task/<pid>/schedstat` : temps CPU du fil principal pendant une action ;
- `simpleperf record --app <paquet> -e cpu-clock -f 4000 -g` : temps CPU par fil et par fonction ;
- `am start -W` (froid après `am force-stop`, chaud après `HOME`) et `dumpsys meminfo <paquet>`.

Une variante sans optimisation ni obfuscation (`-dontoptimize -dontobfuscate`) sert seulement à nommer les
fonctions : R8 fusionne des classes, si bien que certaines lambdas de la build release sont mal attribuées.
Les durées publiées viennent toujours de la build release.

## Scénarios et métriques

Chaque scénario démarre à froid sur le jeu indiqué. Les gestes sont injectés par `adb shell input`.

- **Démarrage** : dix démarrages froids puis dix chauds.
- **Kanto (Rouge) et Hoenn (Rubis)** : seize glissements, puis trois aller-retours du calque « Objets ».
- **Johto (Cristal)** : huit changements d'horaire.
- **Sélection** : Route 1 sélectionnée puis fermée cinq fois ; fiche de Rattata ouverte puis quittée cinq fois.
- **Parc Safari** : recherche, « Voir sur la carte », glissements et calques.
- **Pokédex National (Rubis)** : seize lancers, sprites animés par défaut, partout, puis nulle part.
- **Recherche** : sept saisies (`evoli`, `bourg`…). `input text` n'envoie pas d'accents : la normalisation des
  accents est exercée par des saisies sans accent qui trouvent des noms accentués.
- **Guide** : ouverture de la Soluce de Rouge, cinq fois.
- **Reproduction (Cristal)** : choix successifs des parents.
- **Versions** : deux tours des onze jeux depuis Rouge, mémoire au départ puis après chaque tour.

Pour une action : CPU du fil principal sur la fenêtre (2 à 3,5 s), frame la plus longue, frames au-delà du budget,
plus grand écart entre deux frames successives. Au repos sur la carte, le fil principal consomme 0 ms
(médiane), si bien que le CPU mesuré revient à l'action, animations et menus compris.
`framestats` sous-estime un blocage du fil principal : Choreographer saute alors des vsync et la frame
suivante paraît normale. Le profil simpleperf est donc la mesure de référence pour le travail sur ce fil.
Le pincement n'est pas automatisable avec `input` ; seuls les glissements sont mesurés.

## Référence avant optimisation

Médiane, puis p95 entre parenthèses ; CPU = temps du fil principal pendant l'action.

| Scénario | CPU (ms) | Frame max (ms) | Frames lentes |
|---|---|---|---|
| Démarrage froid / chaud | 527 (528) / 21,5 (40) de `TotalTime` | – | – |
| Glissements Kanto / Hoenn | – | p95 9 / 9, p99 12 / 13 | 2 / 2 sur ≈700 |
| Calque Objets Kanto / Hoenn | 167 (178) / 185 (216) | 10,9 / 27,7 | 0 / 1 |
| Horaire à Johto | 142 (177) | 12,6 (60,1) | 0 |
| Sélection / fermeture de la Route 1 | 94 (132) / 62 (68) | 15,8 / 9,5 | 0 / 0 |
| Ouverture de fiche / retour à la carte | 63 (81) / 86 (99) | 11,3 / 20,1 | 0 / 2 |
| Pokédex National | – | p95 13, p99 15 | 6 sur 711 |
| Recherche (par saisie) | 52,6 (59,7) | 17,2 | 1 |
| Ouverture de la Soluce | 76 (90) | 26,7 | 1 |
| Choix d'un parent | 29 (30) | 14,4 | 0 |
| Affichage de la carte d'un autre jeu | 131 (172) | 24,5 (88,4) | 1 |

Mémoire (`meminfo`) : PSS 224 Mio au départ, 280 Mio après un tour des onze jeux, 280 Mio après le second :
pas de croissance entre deux tours. Pokédex National : PSS 240 Mio sans animation, 260 Mio avec
(tas natif alloué 28,7 contre 38,0 Mio). Sur GrapheneOS, le tas natif apparaît en « Unknown » dans la PSS ;
la colonne `Heap Alloc` reste exacte.

## Attribution du travail sur le fil principal

Profils simpleperf de la build release, temps inclusif cumulé sur le scénario :

- onze changements de jeu : construction du catalogue (`MapRepository.loadCatalog`) 48 ms, index paresseux
  et parcours du catalogue (`partsOf`, `regionsOf`, `floorsOf`, `markerPositions`…) 87 ms, rafraîchissement des
  calques ≈200 ms ;
- cinq sélections et cinq fermetures de zone : `MapSession.refreshOverlays` 241 ms, dont 86 % dans
  `MarkerState.addMarker` de MapCompose. Chaque ajout parcourt et recopie la liste des marqueurs : tout
  redessiner coûte un temps quadratique en nombre de marqueurs, ≈40 ms par sélection de la Route 1 ;
- recherche : lecture et index construits sur le fil principal, ≈30 ms à l'ouverture ;
- Pokédex et fiche Pokémon : repositories et filtrage ≈1 ms au total, rien à déplacer.

## Après optimisation

| Mesure (fil principal, simpleperf) | Avant | Après |
|---|---|---|
| Rafraîchissements, 5 sélections + 5 fermetures | 241 ms | 38 à 48 ms (3 passages) |
| Rafraîchissements, 8 basculements de calque | 44,5 ms | 12,8 ms |
| Rafraîchissements, 4 retours de fiche | 33,5 ms | 14,8 ms |
| Catalogue et index, 11 changements de jeu | 48 + 87 ms | 0 + 4,5 ms |
| Index de recherche | ≈30 ms | 0 ms |
| `hashCode` de l'état du guide, 4 ouvertures de la Soluce | 36 ms | 0 ms |

Le travail retiré du fil principal s'exécute sur `Dispatchers.Default`. Sur des passages alternés, le CPU médian
d'une sélection de zone passe de 102–109 ms à 74–80 ms. Les autres scénarios restent dans le bruit de mesure
(glissements identiques, Pokédex p95 13 ms, mémoire après deux tours 284 Mio, démarrage chaud 24 ms).
Démarrage froid : 534 ms contre 527 ms lors de la campagne ; en alternant ensuite les deux builds, 529,5–533 ms
avant et 533–534 ms après. L'écart reste dans la variation de la référence elle-même.
Les index du catalogue ajoutent ≈24 à 61 Kio par jeu, ≈450 Kio pour les onze catalogues gardés en mémoire
(estimation à partir des cartes, parents et entrées de la base). Les index calculés désormais avec le catalogue
l'étaient déjà au premier affichage : leur mémoire ne change pas.

Ouverture d'un guide : `AnimatedContent` rangeait ses pages dans une table indexée par tout `GuideUiState`,
bibliothèque comprise, et la hachait à chaque frame de la transition. L'état passe désormais dans une enveloppe
comparée par instance. En alternant les builds (cinq ouvertures chacune), le CPU médian d'une ouverture passe de
70,6–74,9 ms à 56,9–65,1 ms, et la frame la plus longue de 28,5–28,8 ms à 21,6–27,9 ms.

## Limites et pistes non traitées

- L'animation des sprites coûte ≈20 Mio de PSS sur le Pokédex National.
- Mesures sur un seul appareil haut de gamme ; un téléphone plus lent amplifie chaque coût du fil principal.
