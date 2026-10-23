# Référence de performance

Mesures du 13 octobre 2026 sur Pixel 6 Pro, GrapheneOS Android 17 (`CP3A.261005.002.A1`), écran 60 Hz
(budget de frame 16,7 ms). Build release minifiée, `profileable`, paquet distinct `org.opensources.pokmaps.perf`,
ART `speed`, statut thermique 0. Ces chiffres sont une référence locale, pas des budgets universels.

## Reproduire une mesure

Un script d’initialisation Gradle local applique dans `androidComponents.finalizeDsl` le suffixe `.perf`,
`profileable = true` et la signature debug à la variante release :
`.\gradlew.bat --init-script <script> assembleRelease`. Le paquet distinct préserve les données debug.
Les symboles R8 sont dans `app/build/outputs/mapping/release/mapping.txt`.

GrapheneOS refuse `linux.ftrace` de Perfetto. Outils utilisables :

- `dumpsys gfxinfo <paquet> reset`, puis `dumpsys gfxinfo <paquet> framestats` : frames et percentiles.
- `/proc/<pid>/task/<pid>/schedstat` : CPU du fil principal sur une fenêtre d’action de 2 à 3,5 secondes.
- `simpleperf record --app <paquet> -e cpu-clock -f 4000 -g` : attribution CPU par fil et fonction.
- `am start -W` après arrêt forcé ou retour HOME, et `dumpsys meminfo <paquet>` : démarrage et mémoire.

Répéter et alterner les builds, garder température et réglages d’animation comparables.
Scénarios : dix démarrages froids/chauds, glissements Kanto/Hoenn, calques, horaires Johto,
sélection/fermeture d’un lieu, ouverture/retour de fiche, défilement du National, saisies de recherche,
ouverture d’un guide, choix de parents et deux tours des onze jeux.
Le pincement n’a pas été automatisé. `framestats` sous-estime certains blocages du fil principal :
utiliser aussi simpleperf. Une build sans optimisation/obfuscation peut aider à nommer les fonctions,
mais les durées de référence viennent de la release.

## Décisions appuyées par les mesures

| Travail sur le fil principal | Avant | Après |
|---|---:|---:|
| Marqueurs, cinq sélections et cinq fermetures | 241 ms | 38–48 ms |
| Catalogue et index, onze changements de jeu | 135 ms | 4,5 ms |
| Construction de l’index de recherche | ≈30 ms | 0 ms |
| Hachage de l’état du guide, quatre ouvertures | 36 ms | 0 ms |

Transformations et index passent sur `Dispatchers.Default` ; les marqueurs sont mis à jour par différence.
`AnimatedContent` compare l’enveloppe d’état du guide par instance, sans hacher toute la bibliothèque à chaque frame.
Les glissements et le Pokédex restaient dans le bruit de mesure ; le démarrage froid restait autour de 530 ms.

Le cache de catalogues conserve les deux dernières versions, avec réutilisation de la géométrie d’une version sœur.
Mesure JVM après GC : environ 2,4 Mio après un tour des jeux, contre 14 Mio auparavant ; relecture d’un jeu
oublié en 16–40 ms hors du fil principal. L’animation du National ajoutait environ 20 Mio de PSS sur téléphone.

Optimisations étudiées et écartées : index SQL supplémentaires (gain 0,1–0,2 ms pour 44 Kio, régressions sur
certaines requêtes) et déduplication des tuiles (environ 3 % de l’APK, nouveau format, aucun gain de fluidité).
Réexaminer ces choix seulement avec de nouvelles mesures. Les résultats sur un seul appareil haut de gamme
ne prédisent pas ceux d’un téléphone plus lent.

## Valider une branche intégrée

Utiliser la release complète sous le paquet distinct `.perf`, avec les assets distribués et les
marqueurs réels. Un banc de tuiles seul ne valide ni les calques, ni les guides, ni les changements de jeu.
Comparer Hoenn, Platine et Diamant/Perle sur leurs cartes régionales, à résolution et fréquence identiques.
Alterner l'ordre sur trois répétitions, relever l'état thermique, puis séparer les scénarios :

- Glissements alternés et pincement à deux contacts dans les deux sens ; garder les événements réellement injectés.
- Calques Dresseurs et Pokémon fixes, désactivés puis réactivés pour restaurer l'état.
- Bibliothèque de soluce définitive, défilement dans les deux sens et retour à la carte.

Conserver `gfxinfo framestats`, `meminfo`, CPU principal et état thermique dans le scratchpad.
Les percentiles de trames ne mesurent pas le temps de chargement ni la latence d'un geste.
Comparer les répétitions et les plages mémoire, en tenant compte du cache et du passage du ramasse-miettes.
Une mesure sur le Pixel 6 Pro ne garantit pas le comportement d'un appareil moins puissant.

## Tests et génération des cartes

Audit local du 21 octobre 2026 sous Windows, Python 3.14 et Pillow 12.3. Les tests et rendus s'exécutent
sur le PC ; ces durées ne concernent pas l'application Android. Les mesures ponctuelles ci-dessous ne
prédisent pas la durée d'une génération complète sur un runner GitHub.

| Contrôle ou échantillon | Avant | Après |
|---|---:|---:|
| Lint debug, avec analyse fraîche des variantes de test | 12 min 57 s | 2 min 03 s |
| Pyramide de 33 tuiles issues de Rouge/Bleu, encodage / réutilisation | 0,182 s | 0,040 s |
| Pyramide de 33 tuiles issues d'Or/Argent, encodage / réutilisation | 0,340 s | 0,028 s |
| Pyramide de 33 tuiles issues d'Émeraude, encodage / réutilisation | 0,742 s | 0,028 s |
| Cadre DS réel de Bonaugure, rendu avec tuiles / réutilisation | 7,448 s | 0,223 s |

Les assemblages de tuiles sont des échantillons composites des assets versionnés ; le coût de lecture et
de placement des sources n'est pas compris. Le cadre DS mesure aussi les neuf tuiles produites.
Le calcul des couleurs DS conserve l'arithmétique entière et évite d'interpoler trois couleurs identiques.
Deux passes par version, alternées après préparation de la géométrie, donnent une médiane de 9,117 s
avant et 6,994 s après sur ce bloc ; des tests de sources concurrents augmentaient la dispersion.
Les quatre passes ont produit exactement les mêmes pixels que le moteur original.

La première génération remplit le cache et peut coûter un peu plus cher que l'encodage seul. La clé d'une
pyramide dépend de ses pixels, dimensions, niveaux et encodeur. Celle d'un cadre DS dépend de ses triangles,
textures décodées, cadrage, plafonds et code du moteur. Les catalogues et données restent assemblés et validés.
`generation-report.json` indique les cadres DS effectivement réutilisés (`frame_cache_hits`).
Les tests de rasterisation gardent un chemin sans cache ; le test de reconstruction compare les assets complets.
Sur les deux passages de ce test, la préparation est passée de 639,52 s à 446,59 s ; sa vérification complète
est ensuite passée de 69,74 s à 66,83 s. Les caches et les accès disque étaient différents entre les passages.
L'audit des 389 tests de sources a aussi montré deux exports DS redondants de 132 à 134 s chacun : les tests
de positions utilisent maintenant les exports paresseux déjà construits pour leur session. Les cartes
d'Or/Argent et Cristal, les référentiels PokéAPI et les cartes GBA analysées sont également partagés.

Un cache distinct pour chaque tuile a été mesuré puis écarté : sur ces petits fichiers, ses lectures et
vérifications coûtaient davantage que l'encodage. Le cache retient donc une pyramide entière dans un seul fichier.
Les résultats et scripts de mesure locaux restent dans `tools/build/scratchpad/render-audit/`.

## Recette HGSS du 23 octobre 2026

Pixel 6 Pro, GrapheneOS Android 17 (`2026102101`), écran 1440 × 3120 à 60 Hz. Les assets sont ceux des
seize jeux activés, sans régénération pendant les contrôles. La variante release minifiée utilise le
paquet distinct `.perf`, `profileable` et la signature debug locale, selon la procédure ci-dessus.
Elle est reconstruite après la correction du libellé des lieux ; aucun APK de distribution signé en CI
n'est produit. ART est compilé avec `cmd package compile -m speed -f org.opensources.pokmaps.perf`.

Le protocole conserve les sprites animés partout, les horaires sur Tout et le réseau coupé (mode avion
et Wi-Fi explicitement désactivé). Chaque passage ouvre la carte régionale, attend son chargement,
puis effectue huit glissements alternés de 500 ms, entre x = 1100 et 340, à y = 1500. Deux pincements
à contacts simultanés font varier le demi-écartement de 150 à 400 pixels, puis l'inverse, autour de
(720, 1500), avec 24 mouvements espacés de 20 ms. Chaque événement injecté doit être accepté.
Les traces du pilote conservent les deux confirmations ; les gestes ne sont pas supposés à partir
de la seule variation du zoom. Les cartes HGSS commencent à Bourg Geon, Émeraude à Bourg-en-Vol
et Platine à Bonaugure. Trois répétitions inversent l'ordre des quatre jeux une fois sur deux.

`gfxinfo framestats` est remis à zéro pour chaque passage ; `meminfo`, `thermalservice` et le temps CPU
du fil principal (`schedstat`) sont conservés. Les durées incluent les glissements et les pincements ;
le CPU est un cumul sur le passage, pas une durée par trame. Les percentiles concernent les trames
effectivement enregistrées, pas la latence d'un geste ou le temps de chargement. Le nombre de trames
dépend aussi des animations : il ne mesure pas directement le nombre d'images par seconde de la carte.

Les percentiles et le CPU ci-dessous sont les médianes des trois passages. Les trames saccadées sont
additionnées, avec leur dénominateur ; la mémoire donne la plage des trois relevés, sans la convertir
en pic garanti. L'état thermique vaut 0 sur les douze passages.

| Jeu | p50 / p95 / p99 (ms) | Saccades / trames | PSS (Mio) | CPU principal (ms) |
|---|---:|---:|---:|---:|
| Émeraude | 6 / 10 / 11 | 3 / 1 240 | 223,3–238,9 | 1 203 |
| Platine | 6 / 11 / 13 | 3 / 1 237 | 230,5–241,6 | 1 304 |
| Or HeartGold | 7 / 10 / 11 | 2 / 715 | 222,3–229,9 | 962 |
| Argent SoulSilver | 6 / 8 / 10 | 1 / 666 | 213,5–244,8 | 830 |

HGSS se situe dans la plage de ces références locales pour les cartes mesurées. Les scènes n'ont pas
la même géométrie ni le même nombre de marqueurs : ces résultats ne prouvent pas l'égalité des coûts
de rendu ni une absence universelle de régression. Ils ne sont pas une comparaison avant/après avec
la build du 13 octobre. Aucun seuil de performance universel n'est déduit de ce seul téléphone.

Une mesure préliminaire debug, sur huit glissements sans pincement, donnait des p95 de 13 à 18 ms,
des p99 de 18 à 38 ms et une PSS de 285,6 à 450,1 Mio. Ces pointes restent dans les journaux ;
la différence de variante et de protocole ne permet pas d'en déduire un facteur d'accélération.

L'APK debug final pèse **330 961 489 octets (315,63 Mio)** et la variante minifiée de mesure
**292 511 433 octets (278,96 Mio)**. Cette dernière est signée avec la clé debug, avec un paquet et
des métadonnées de profilage propres : sa taille n'est pas celle d'une future release signée en CI.
Les fichiers suivis sous `app/src/main/assets/` totalisent **329 671 256 octets (314,40 Mio)**.

Les scripts, mesures brutes et captures de la session sont dans `tools/build/scratchpad/phase8-recette/`.
La [recette fonctionnelle](../plan4g%20remake.md) conserve les preuves de sauvegarde et d'installation,
les contrôles exécutés et les limites. Ces mesures sur un seul appareil ne qualifient pas un téléphone
moins puissant ; elles ne remplacent pas une mesure de démarrage, de chargement ou de consommation.
