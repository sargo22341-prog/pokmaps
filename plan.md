# Pokémaps — Plan du projet

Application Android de cartes interactives et Pokédex pour **Pokémon Rouge, Bleu et Jaune**, entièrement en français,
conçue pour accueillir ensuite les autres jeux (Or/Argent/Cristal, Rubis/Saphir…).

Modèle : [pokemaps.net](https://pokemaps.net/maps/rby/kanto/) — carte et Pokédex liés dans les deux sens
(de la carte vers le Pokédex et inversement).

## Objectifs

- Carte de Kanto **pixel-art fidèle au jeu**, zoomable, avec les lieux cliquables
- Au clic sur un lieu : les Pokémon (version, niveaux, probabilité, méthode : herbes, surf, cannes, dons, échanges…)
- Au clic sur un Pokémon : la fiche complète (stats, types, évolutions, attaques par niveau, CT/CS) et **tous ses lieux surlignés sur la carte**
- Pokédex avec recherche
- 100 % hors-ligne pour les données et les sprites

## Contraintes

- **Kotlin**, Jetpack Compose
- **minSdk = Android 17 (API 37)**, sans rétrocompatibilité
- **Aucun service Google Play** (cible : GrapheneOS) : pas de Firebase, Play Services, Google Maps ni Play Integrity
- Usage personnel : distribution par **GitHub Releases** (pas de Play Store)
- Ne rien récupérer de pokemaps.net : on utilise **les mêmes sources** que lui (voir ci-dessous), et les cartes sont générées par ce projet

## Sources de données

Ce sont les sources citées par pokemaps.net (« Species and encounter data build on PokeAPI […] Box sprites and item
icons come from the pokesprite project; official artwork is served via PokeAPI/sprites »).

| Source | Utilisation | Licence / conditions |
|---|---|---|
| **[PokéAPI](https://pokeapi.co)** — export CSV du dépôt [PokeAPI/pokeapi](https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv) | **Source principale** : Pokémon, noms et descriptions en français, types et stats par génération, attaques par jeu, CT/CS, évolutions, Pokédex régionaux, lieux et zones (noms FR), rencontres par version (herbes, surf, cannes, dons, échanges, Pokémon fixes, conditions), table des types par génération | Données BSD-3. [Usage équitable](https://pokeapi.co/docs/v2#fairuse) : on télécharge les CSV **une fois au build**, avec cache ; l'application n'appelle jamais l'API |
| **[msikma/pokesprite](https://github.com/msikma/pokesprite)** | Icônes de boîte des Pokémon (`pokemon-gen8/regular`) et icônes d'objets (Poké Balls, pierres, CT/CS par type) | Code MIT ; images © Nintendo / Game Freak |
| **[PokeAPI/sprites](https://github.com/PokeAPI/sprites)** | Sprites des jeux embarqués (`versions/generation-i/red-blue`, `yellow`) ; artworks officiels (`other/official-artwork`) chargés en ligne avec cache, en option | Images © Nintendo / Game Freak |
| **`tools/data/`** (saisie manuelle, relue) | Couche de corrections : noms français corrigés (accents, étages), notes (prix du Casino, Pokémon à échanger, « un seul au choix »), doublons retirés | Ce projet |
| **[pret/pokered](https://github.com/pret/pokered)**, **[pret/pokeyellow](https://github.com/pret/pokeyellow)** | **Uniquement pour les cartes** : blocs, tilesets, palettes, connexions, objets, PNJ, warps (fichiers sources du dépôt, aucune ROM) | Désassemblages communautaires |
| Plus tard : [Bulbapedia](https://bulbapedia.bulbagarden.net) (CC BY-NC-SA), export de données PokeDB | Disponibilités des générations récentes absentes de PokéAPI, comme le fait pokemaps.net | À créditer dans l'app |

Règles :
- Toutes les sources sont **figées sur un commit** (`tools/pokemaps_data/sources.py`) : la génération est reproductible.
- On corrige PokéAPI **uniquement via `tools/data/`**, jamais en modifiant les CSV. Chaque correction doit
  correspondre à une donnée existante (la build échoue sinon), ce qui détecte les corrections devenues inutiles.
- Ajouter un jeu = ajouter une ligne dans `tools/pokemaps_data/games.py` (groupe de versions PokéAPI + dossier de sprites).
- Écran « À propos » de l'app : créditer PokéAPI, pokesprite, PokeAPI/sprites, pret, et © Nintendo / Creatures / GAME FREAK.

## Stack technique

| Rôle | Choix |
|---|---|
| UI | Jetpack Compose + Material 3 |
| Architecture | MVVM (ViewModel + StateFlow), Hilt |
| Données | Room, base SQLite pré-remplie (`createFromAsset`) |
| Recherche | Room FTS4 (insensible aux accents) |
| Carte | MapCompose (`ovh.plrapps:mapcompose`), carte en tuiles |
| Images | Coil (sprites depuis les assets, artworks en ligne avec cache disque) |
| Navigation | Navigation Compose |
| Pipeline de données | Script Python dans `tools/` (stdlib + Pillow, pytest, ruff) |
| CI/CD | GitHub Actions |

---

# TODO

## Phase 0 — Mise en place du dépôt ✅
- [x] Créer le projet Android (Gradle Kotlin DSL, version catalog `libs.versions.toml`)
- [x] Configurer `minSdk = 37`, `targetSdk = 37`, `compileSdk = 37`
- [x] Ajouter `.gitignore`, `README.md` et la licence (MIT)
- [x] Mettre en place ktlint (tâches `ktlintCheck` / `ktlintFormat`) et Android Lint
- [x] Vérifier qu'aucune dépendance ne tire `com.google.android.gms`, `com.google.firebase` ou Play Core (tâche `checkNoGoogleServices`, lancée en CI)

## Phase 1 — CI/CD (GitHub Actions) ✅
- [x] Workflow `ci.yml` (push et PR) : lint, tests unitaires, build de l'APK debug
- [x] Mise en cache de Gradle et des sources de données
- [x] Étape de génération des données (`tools/`) dans la CI
- [x] Générer un keystore de release et l'ajouter aux secrets GitHub (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`)
- [x] Workflow `release.yml` (sur tag `v*`) : build de l'APK release signé et publication dans **GitHub Releases**
- [x] Versionnage automatique (`versionCode` et `versionName` depuis le tag)
- [x] Documenter l'installation et les mises à jour via **Obtainium** (suivi des GitHub Releases sur GrapheneOS)
- [x] Publier l'APK debug comme artefact de workflow

## Phase 2 — Pipeline de données (`tools/build_data.py`) ✅
- [x] Télécharger les CSV PokéAPI, les icônes pokesprite et les sprites PokeAPI/sprites (commits figés, cache local)
- [x] Configuration des jeux (`games.py`) : Rouge/Bleu et Jaune ; schéma prêt pour plusieurs générations
- [x] Pokémon : noms FR/EN, catégorie, description FR, taille, poids, taux de capture, courbe d'expérience, légendaire / fabuleux
- [x] Types et stats **par génération** (types d'origine, stat « Spécial » de la 1re génération)
- [x] Table des types par génération (Spectre sans effet sur Psy en 1re génération…)
- [x] Attaques **par jeu** grâce à l'historique PokéAPI (Morsure de type Normal en 1re génération…) et catégorie physique / spéciale selon le type jusqu'à la 3e génération
- [x] Attaques apprises par jeu (niveau, CT/CS), CT/CS de chaque jeu
- [x] Évolutions valables dans chaque jeu (pas de Mentali ni de Noctali en 1re génération)
- [x] Pokédex régionaux (Kanto) et numéros
- [x] Lieux et zones avec noms FR, rencontres par version regroupées (probabilités en %, niveaux, nombre d'exemplaires, conditions comme « en ayant un Nautile »)
- [x] Couche de corrections `tools/data/` : noms FR (`name_fixes.csv`), notes et doublons (`encounter_curation.csv`)
- [x] Images embarquées : icônes de boîte, sprites Rouge/Bleu et Jaune, icônes d'objets
- [x] Tests de cohérence : références valides, probabilités à 100 %, chaque Pokémon obtenable, valeurs 1re génération vérifiées

## Phase 3 — Génération des cartes pixel-art ✅
- [x] Lecteur des désassemblages pret (`tools/pokemaps_data/pret.py`) : cartes, blocs, tilesets, connexions, warps, objets, PNJ, objets cachés, palettes Super Game Boy
- [x] Renderer : blocs et tilesets pret → image de chaque carte, aux couleurs Super Game Boy (palette de chaque ville, bâtiments à la couleur de leur ville)
- [x] Assembler la carte du monde de Kanto (villes et routes reliées via les connexions de cartes, bordure du jeu autour)
- [x] Générer les cartes intérieures accessibles (grottes, Tour Pokémon, Sylphe SARL, Manoir Pokémon, Parc Safari, Route Victoire, Caverne Azurée, bâtiments…) — **une série par jeu** : Jaune a des cartes différentes (Centres Pokémon, Route 4, grottes…)
- [x] Noms français de chaque carte (`tools/data/maps.csv`)
- [x] Table de correspondance cartes pret ↔ zones PokéAPI (`tools/data/map_areas.csv`), vérifiée (toute zone avec des rencontres doit avoir sa carte dans chaque jeu)
- [x] Découper chaque carte en tuiles WebP sans perte de 256 px pour MapCompose (niveaux de zoom, tuiles vides omises ; l'app agrandit sans lissage)
- [x] Exporter les coordonnées (en pixels) de chaque carte, zone, objet, objet caché, dresseur, Pokémon fixe, PNJ et warp (avec sa destination) dans la base (`map`, `map_area`, `map_warp`, `map_object`)
- [x] Sprites des PNJ et objets (vue de face) pour les calques de la carte
- [x] Intégrer les tuiles dans les assets de l'app (~2 Mo pour les deux jeux)

## Phase 4 — Squelette de l'app
- [ ] Mise en place de Hilt, Room (`createFromAsset`) et Navigation Compose
- [ ] Entités et DAO Room calqués sur `tools/pokemaps_data/schema.sql` (version de base = `SCHEMA_VERSION`)
- [ ] Repositories et cas d'usage
- [ ] Sélecteur de jeu global (Rouge / Bleu / Jaune), mémorisé avec DataStore : il fixe la version, le groupe de versions et la génération utilisés partout
- [ ] Barre de navigation : Carte / Pokédex
- [ ] Écran « À propos » avec les crédits des sources

## Phase 5 — Pokédex
- [ ] Liste ou grille du Pokédex du jeu choisi (icône pokesprite, numéro régional, nom, types de la génération)
- [ ] Recherche par nom (FTS, accents ignorés : « evoli » trouve « Évoli ») et par numéro
- [ ] Filtres : type, disponible dans la version choisie, méthode d'obtention
- [ ] Tests unitaires du ViewModel

## Phase 6 — Fiche Pokémon
- [ ] En-tête : sprite du jeu (ou artwork officiel en ligne si disponible), numéro, nom, catégorie, types
- [ ] Stats de base de la génération (PV, Attaque, Défense, Vitesse, Spécial en 1re génération)
- [ ] Faiblesses et résistances (table des types de la génération)
- [ ] Chaîne d'évolution cliquable (niveau, pierre avec son icône, échange)
- [ ] Attaques par niveau et CT/CS du jeu choisi (type, catégorie, puissance, précision, PP)
- [ ] Lieux de capture (version, méthode, niveaux, probabilité, notes) et bouton « Voir sur la carte »
- [ ] Meilleure Poké Ball : probabilité de capture selon la balle, les PV et le statut (formule de la génération, taux de capture PokéAPI)

## Phase 7 — Carte interactive
- [ ] Afficher la carte de Kanto avec MapCompose (zoom, déplacement, limites)
- [ ] Zones cliquables de chaque lieu
- [ ] Fiche en bas d'écran au clic : nom de la zone et Pokémon par méthode, filtrés par version
- [ ] Accès aux cartes intérieures depuis les entrées (grottes, bâtiments, étages)
- [ ] Mode « surlignage » : zones d'un Pokémon mises en évidence, avec recentrage automatique
- [ ] Calques activables : objets, dresseurs, warps
- [ ] Clic sur un Pokémon de la fiche → fiche Pokémon

## Phase 8 — Finitions
- [ ] Recherche globale (Pokémon et lieux)
- [ ] Favoris ou Pokémon capturés (suivi de progression par version)
- [ ] Tests UI Compose sur les parcours principaux
- [ ] Optimisation de la taille de l'APK (WebP des tuiles, R8)
- [ ] Captures d'écran dans le README
- [ ] Première release `v1.0.0`

## Plus tard (idées)
- [ ] Écran dédié à la table des types de chaque génération
- [ ] Calculateur de stats et DV
- [ ] Extension à Or/Argent/Cristal (Johto + Kanto) : ajouter `gold-silver` et `crystal` dans `games.py`, gérer les conditions matin / jour / nuit, générer les cartes depuis pret/pokecrystal
- [ ] Extension à Rubis/Saphir/Émeraude, Rouge Feu/Vert Feuille…
