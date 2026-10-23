# Pokémaps

Application Android en français : cartes interactives, Pokédex et guides pour **Rouge, Bleu, Jaune,
Or, Argent, Cristal, Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille, Diamant, Perle et Platine**.

- Android 17 (API 37), Kotlin et Jetpack Compose.
- Fonctionne sur GrapheneOS, sans services Google Play.
- Cartes, sprites, données et guides embarqués, utilisables hors ligne.
- RetroAchievements facultatif : lecture de la progression, sur synchronisation manuelle uniquement.

## Installer

Télécharger l’APK depuis les [GitHub Releases](https://github.com/sargo22341-prog/pokmaps/releases).
Pour les mises à jour avec [Obtainium](https://github.com/ImranR98/Obtainium), ajouter
`https://github.com/sargo22341-prog/pokmaps` comme source. Aucune distribution sur le Play Store.

## Utiliser

Choisir une version dans l’onglet Jeu. Toucher un lieu sur la carte pour consulter ses rencontres,
objets et personnages ; les fiches du Pokédex permettent de retrouver leurs lieux sur la carte.
Les icônes de combat restent au-dessus des sprites, avec une icône commune aux duos ; les PNJ sont placés
à distance des passages pour laisser leur accès visible. Les figurants temporaires devant les portes sont
retirés lorsqu'ils n'ajoutent aucun combat ni service ; les PNJ permanents restent affichés.
À Sinnoh, les personnages sont présentés de face et les duos adjacents sont espacés.
Les combats de scénario sont rattachés aux personnages, avec un sélecteur de Pokémon de départ
pour les équipes variables. Les poses techniques et les décors sans sprite ni interaction utile
ne créent pas de repères ; les services sans image disposent d’une icône d’information.
Les guides regroupent soluces, quêtes, astuces et succès officiels traduits.
Les listes des routes affichent par défaut les rencontres ordinaires, sans cartouche GBA insérée.
Des filtres séparent les Pokémon errants et activent les conditions disponibles (cartouche GBA,
Pokédex National, Pokéradar, essaim). Les périodes disponibles se combinent avec des boutons à icônes ;
Tout les réactive et les lieux sans variation horaire masquent ces boutons.
Seuls les Pokémon des horaires sélectionnés restent visibles ; les Pokémon offerts ont leur filtre dédié, comme les
errants.
Les échanges suivent les rencontres sauvages.
À Sinnoh, les objets ramassés par lots indiquent leur quantité sur la carte et dans les listes des lieux.
Dans Rouge, Bleu et Jaune, le rival de la Route 22 partage un seul repère pour ses deux combats.
Dans Jaune, seuls les combats à équipe variable affichent les choix de victoires et défaites précédentes.
Les dresseurs présentent leur équipe initiale et six Poké Balls, grisées pour les places vides ;
un menu compact permet de choisir un autre combat. Leur fiche se ferme aussi en glissant vers le bas.
Changer de jeu depuis une fiche Pokémon absente de la nouvelle génération ramène au Pokédex.

Les horaires et les types d’arbres sont réunis par Pokémon, avec leurs icônes et probabilités.
Les trois horaires gardent leurs couleurs et seuls les horaires absents sont grisés.
À pied, les colonnes horaires précèdent le sprite et le nom dans une carte par Pokémon ;
chaque niveau et sa probabilité se lisent sur une même ligne.
Les arbres partagent un titre ; chaque icône affiche son taux, avec des flèches pour les arbres à taux élevé.
Les sections forêt, marche et eau utilisent des cartes espacées laissant voir le décor.
Les rencontres aquatiques regroupent chaque Pokémon par lieu, avec quatre icônes dans l’ordre
Surf, Canne, Super Canne et Méga Canne. Chaque méthode affiche ses probabilités et niveaux ;
les méthodes indisponibles sont grisées, sans libellé visible.
La section « Zone d’eau » sépare ces rencontres de la marche ; chaque Pokémon a un encadré
avec ses icônes et probabilités au-dessus de son sprite et de son nom.
Les fonds fixes reprennent uniquement les tuiles d’Émeraude pour tous les jeux : herbes, sous-bois,
grotte, glace, sable ou sol intérieur. Une rive de lac assortie entoure l’eau et les cartes aquatiques
ont un fond dépoli ; leurs textes restent nets. Toutes les rencontres hors eau, y compris celles
du matin, du jour et de la nuit, précèdent l’unique bloc aquatique.

Les cartes de rencontres de Rouge, Bleu, Jaune, Rubis, Saphir, Émeraude, Rouge Feu et Vert Feuille
masquent les horaires matin, jour et nuit : niveaux et probabilités ne sont affichés qu’une fois.
Les horaires restent disponibles dans Or, Argent, Cristal, Diamant, Perle et Platine.

Captures, formes de Zarbi et progression sont mémorisées localement. Les Réglages proposent
la portée des captures, les animations, la sauvegarde JSON et la connexion RetroAchievements.
L’application ne lit aucune sauvegarde de cartouche et ne prédit aucun tirage du jeu.

| Carte | Pokédex | Fiche Pokémon |
|---|---|---|
| ![Carte][carte] | ![Pokédex][pokedex] | ![Pikachu][pokemon] |

[carte]: docs/screenshots/carte.webp
[pokedex]: docs/screenshots/pokedex.webp
[pokemon]: docs/screenshots/pokemon.webp

| Carte de Platine | Pokédex de Diamant | Carte de Perle |
|---|---|---|
| ![Sinnoh dans Platine][platine] | ![Pokédex Sinnoh de Diamant][diamant] | ![Sinnoh dans Perle][perle] |

[platine]: docs/screenshots/sinnoh-platinum-map.png
[diamant]: docs/screenshots/sinnoh-diamond-pokedex.png
[perle]: docs/screenshots/sinnoh-pearl-map.png

## Documentation

Lire [AGENTS.md](AGENTS.md) avant toute modification, puis uniquement les pages utiles à la tâche
via [l’index](docs/README.md).

| Besoin | Référence |
|---|---|
| Compiler, vérifier, installer en debug | [Développement](docs/developpement.md) |
| Sources, génération et éditeur de cartes | [Pipeline](docs/donnees/pipeline.md) |
| Fonctionnement des écrans | [Documentation fonctionnelle](docs/README.md#fonctionnement) |
| Particularités des jeux | [Générations](docs/README.md#jeux-et-règles) |
| Diamant, Perle et Platine | [Génération 4](docs/generations/generation-4.md) |
| Mesurer une optimisation | [Performances](docs/performance.md) |

`app/` contient l’application ; `tools/` le pipeline Python ; `tools/data/` les données éditoriales.
Les assets finaux et leur inventaire SHA-256 sont versionnés. Les builds Android les réutilisent
sans génération ni téléchargement de contenu Pokémon. Les sources brutes et caches restent hors Git.
`python tools/verify.py` lance les contrôles Python et Android sans régénérer les cartes ; `--scope android`
ou `--scope python` limite le travail à la partie modifiée. Les rendus des quatre générations utilisent
un cache vérifié par leur contenu lors des générations explicites.
Les sources principales sont PokéAPI, PokeAPI/sprites, pokesprite et les dépôts pret ; aucune ressource
n’est récupérée sur pokemaps.net. Leur rôle est détaillé dans le pipeline.

HeartGold/SoulSilver disposent d'une [qualification des sources](docs/generations/sources-hgss.md)
et d'un contrat préparatoire isolé des jeux générables. Ils ne sont pas encore disponibles dans l'application.
Android reconnaît leur identité préparatoire et leurs [règles de capture](docs/generations/regles-android-hgss.md),
sans les ajouter au catalogue distribué ; les tests injectent les deux remakes séparément de la base embarquée.
Leurs outils préparatoires appliquent les règles propres de reproduction (Pierre Stase et objets Pouvoir)
et de bonheur. Le même export JSON préserve les collections et les dernières routes observées des errants
de Sinnoh et des deux remakes, avec import des anciens fichiers ; aucune progression GSC n’est copiée vers HGSS.
Leur [aperçu cartographique](docs/generations/cartes-hgss.md) se génère sans ROM avec
`python tools/build_data.py --hgss-maps-only --map-workers 4` dans `tools/build/preview/hgss-maps/`.
Il conserve les cinq lieux témoins et le catalogue Johto, puis ajoute un
[atlas complet](docs/generations/cartes-hgss-atlas.md) : 496 cartes et gabarits nommés en français dans les deux régions
et les installations, portes, voisinages DS, transports scriptés et coupes des surfaces superposées.
Les décors créés par les arènes sont placés dans leur état initial ; les destinations variables et les branches
de scénario restent identifiées. `python tools/review_hgss_maps.py` produit les planches
de relecture dans le scratchpad ; `python tools/check_assets.py --hgss-maps tools/build/preview/hgss-maps`
vérifie l'inventaire, les images, les plans, les coupes et leurs références. Les jeux restent préparatoires.
Leur [aperçu Pokémon indépendant](docs/generations/pokemon-hgss.md) se génère avec
`python tools/build_data.py --hgss-pokemon-only` dans `tools/build/preview/hgss-pokemon/` :
493 espèces, régional Johto, attaques, CT/CS, formes et évolutions, sans activation Android.
L’[aperçu des rencontres HGSS](docs/generations/rencontres-hgss.md) se génère après les cartes avec
`python tools/build_data.py --hgss-encounters-only` : marche, eau, pêche, horaires, radio, essaims,
arbres et Éclate-Roc, concours selon le jour et le National, Safari selon les blocs et la maturation,
avec distributions conditionnelles et écarts PokéAPI classés. Les obtentions particulières conservent
leur provenance et leurs exclusions par événement, transfert ou accessoire, sans prédiction de disponibilité.
Les filtres de rencontres distinguent Coup d’Boule et Éclate-Roc ; les remakes restent préparatoires.
Le placement se vérifie avec `python tools/build_data.py --hgss-placement-only`, puis se relit avec
`python tools/map_editor.py --assets tools/build/preview/hgss-placement`.
Les points de Johto, Kanto et des gabarits Safari restent dans `tools/data/map_spots.csv` ;
les terrains sans marqueur ont une [explication explicite](docs/generations/rencontres-hgss.md#placement--4e).
Les [personnages, combats et services HGSS](docs/generations/personnages-hgss.md) se génèrent avec
`python tools/build_data.py --hgss-characters-only` dans `tools/build/preview/hgss-characters/`.
Ouvrir `index.html` pour parcourir les personnages, leurs placements, les revanches et les offres hors ligne.
Le catalogue relie 737 équipes, 123 combats de scénario résolus, 63 séries de revanches et 567 offres ;
les sprites, quantités, coûts et étapes sont vérifiés depuis les sources HGSS épinglées.

L’aperçu Pokémon de Diamant, Perle et Platine se génère séparément avec
`python tools/build_data.py --sinnoh-pokemon-only` dans `tools/build/preview/sinnoh-pokemon/`.
Il contient les données Pokémon et leurs sprites ; les cartes DS et l’activation dans l’application restent séparées.

Les cartes préparatoires de Sinnoh se génèrent avec
`python tools/build_data.py --sinnoh-maps-only --map-workers 8` dans `tools/build/preview/sinnoh-maps/`.
Les deux familles ont leurs propres tuiles, catalogues français, étages, niveaux inférieurs et liaisons.
`python tools/review_gen4_maps.py` produit les planches de relecture dans le scratchpad.
Ensuite, `python tools/build_data.py --sinnoh-encounters-only` ajoute les rencontres lues dans le moteur DS et les
emplacements sauvages dans `tools/build/preview/sinnoh-encounters/`, que l’éditeur ouvre avec `--assets`.
`python tools/build_data.py --sinnoh-characters-only` écrit dans `tools/build/preview/sinnoh-characters/` les
dresseurs, combats de scénario, revanches du Cherche VS, objets des lieux, Pokémon fixes, noms français, étapes du
scénario et le déblocage du Pokédex National.
L'aperçu comprend aussi les offres des personnages et des installations : dons, œufs, stocks des boutiques
selon les badges, échanges, tuteurs, soins, baies et paillis, fossiles, Pension, Casino et Maître des Capacités.
Les conditions des offres sont traduites en français et gardent leur provenance brute ; les prix, monnaies et
coûts en Tessons restent distincts. Les lots échangés ensemble conservent leur paiement unique.
Chaque offre garde son origine : PNJ posé avec son drapeau de retrait, ou scène, case et déclencheur.
Les exemplaires d'un personnage à plusieurs étapes restent distincts dans cet aperçu.
La curation annote les figurants temporaires et attribue les dons de scène au personnage qui les remet.
La génération complète intègre les catalogues DS validés et active Diamant, Perle et Platine dans l’application.
Si les cartes préparatoires manquent, elle les reconstruit depuis les sources épinglées.
`--application-only` limite la génération aux jeux actifs, sans reconstruire un aperçu supplémentaire.
La carte propose des sélecteurs distincts pour les étages et les niveaux superposés de Sinnoh.
Les salles DS d'un même étage sont réunies en plans, avec les liaisons entre leurs portes.
Les poses alternatives des agents et joggers partagent un seul repère et les Pokémon fixes restent
à leur position permanente ; sans animation, leur sprite de terrain est présenté de face.
Le calque Arbres à Miel apparaît uniquement sur les cartes qui contiennent leurs emplacements ;
les plantations affichent leur baie et leur récolte initiales, puis permettent de replanter dans le jeu.
Les lieux, rencontres et offres événementiels gardent la mention
« événement externe ». La sauvegarde de collection accepte les versions 12 à 14 et leurs 493 espèces,
et conserve l’import des anciens fichiers de schéma 1.
Les modèles Android reconnaissent ces trois versions (493 espèces) et affichent leur rangée
« 4e génération ». Les filtres distinguent les arbres à Miel et les dons de Pokémon Ranger.
Le calculateur DS gère Sombre, Soin et Rapide Ball, le terrain aquatique, le Grand Marais et le Parc des Amis ;
la Mémoire Ball reste réservée aux distributions.
Le Pokédex DS propose la bascule Sinnoh/National et les deux numéros sur la fiche. Les formes retenues ont
leurs sprites normaux et chromatiques et leur suivi de collection ; Zarbi conserve ses 28 formes.
Les fiches utilisent la classe propre à chaque attaque et les conditions d’évolution DS en français.
Les guides de Sinnoh proposent une soluce adaptée à chaque version, des quêtes, conseils, bugs documentés
et un calendrier des rendez-vous. Deux objectifs suivent les captures accessibles sur une cartouche seule,
dans le régional puis le National, en tenant compte des starters et fossiles incompatibles.
Les succès officiels des quatorze jeux sont traduits et consultables hors ligne ; leur synchronisation
RetroAchievements reste manuelle. Les outils de Sinnoh appliquent ses règles de reproduction et de bonheur.
Les dernières routes observées des errants se notent par cartouche et entrent dans la sauvegarde JSON.
Les fiches des baies de Sinnoh détaillent croissance, arrosage, paillis et saveurs pour Poffins ; les attaques
présentent leurs effets de Super Concours. Les guides recensent les fouilles, pièges et décorations du Souterrain,
ainsi que les configurations possibles par série de la Tour et des installations de Platine.
Ils distinguent locations de l’Usine et rangs de la Scène, sans simuler les mini-jeux ni les tirages.
Ce catalogue se régénère avec `python tools/build_data.py --sinnoh-content-only` ; ses sources et règles sont
décrites dans [les contenus de Sinnoh](docs/generations/contenus-sinnoh.md).

## Publier une version

Configurer une fois les secrets GitHub Actions `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`
et `KEY_PASSWORD`, à partir d’un keystore conservé hors du dépôt. Exemple de création :

```bash
keytool -genkeypair -v -keystore pokemaps-release.jks -alias pokemaps \
  -keyalg RSA -keysize 4096 -validity 10000
base64 -w 0 pokemaps-release.jks > pokemaps-release.jks.base64
```

Conserver la clé et ses mots de passe : ils sont nécessaires pour installer les futures mises à jour.
La signature release s’effectue uniquement en CI.

Après les [contrôles](docs/developpement.md), inclure les assets et leurs empreintes dans le commit
à publier, ainsi qu’une courte note française sous `<!-- notes -->` dans [RELEASE_NOTES.md](RELEASE_NOTES.md)
pour chaque changement visible. Puis pousser un tag `vMAJEUR.MINEUR.CORRECTIF` ou lancer le workflow
Release manuellement avec cette version. Mineur et correctif sont inférieurs à 100 ; le code Android
vaut `MAJEUR × 10000 + MINEUR × 100 + CORRECTIF`.

Le workflow publie l’APK signé et son SHA-256, puis vide les notes publiées si celles de `main`
sont encore identiques. Ne jamais vider cette liste à la main.

## Mentions légales

Projet de fan, personnel et non commercial. Pokémon et les noms associés sont des marques de Nintendo,
Game Freak et The Pokémon Company ; les images sont © Nintendo, Creatures et GAME FREAK.
Aucune ROM ni ressource extraite d’une ROM. Code sous licence [MIT](LICENSE).
