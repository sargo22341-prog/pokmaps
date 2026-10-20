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
