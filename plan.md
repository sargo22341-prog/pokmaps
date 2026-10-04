# Pokémaps — Plan du projet

Application Android de cartes interactives pour **Pokémon Rouge, Bleu et Jaune**, entièrement en français.

## Objectifs

- Carte de Kanto **pixel-art fidèle au jeu**, zoomable, avec les lieux cliquables
- Au clic sur un lieu : les Pokémon sauvages (version, niveaux, taux, méthode)
- Au clic sur un Pokémon : la fiche complète (stats, évolutions, attaques par niveau, CT/CS) et **tous ses lieux surlignés sur la carte**
- Pokédex avec recherche
- 100 % hors-ligne

## Contraintes

- **Kotlin**, Jetpack Compose
- **minSdk = Android 17 (API 37)**, sans rétrocompatibilité
- **Aucun service Google Play** (cible : GrapheneOS) : pas de Firebase, Play Services, Google Maps ni Play Integrity
- Usage personnel : distribution par **GitHub Releases** (pas de Play Store)
- Ne rien récupérer de pokemaps.net : les cartes sont générées depuis le désassemblage **pret**

## Stack technique

| Rôle | Choix |
|---|---|
| UI | Jetpack Compose + Material 3 |
| Architecture | MVVM (ViewModel + StateFlow), Hilt |
| Données | Room, base SQLite pré-remplie (`createFromAsset`) |
| Recherche | Room FTS4 (insensible aux accents) |
| Carte | MapCompose (`ovh.plrapps:mapcompose`), carte en tuiles |
| Images | Coil |
| Navigation | Navigation Compose |
| Pipeline de données | Script Python dans `tools/` (stdlib, pytest, ruff) |
| CI/CD | GitHub Actions |

## Sources de données

- **pret/pokered** et **pret/pokeyellow** : rencontres, attaques par niveau, évolutions, stats, CT/CS, cartes (blocs et tilesets), objets, PNJ, warps
- **PokéAPI** (CSV de `PokeAPI/pokeapi`, dossier `data/v2/csv`) : noms français des Pokémon, attaques et types
- **Saisie manuelle** : noms français des lieux, rencontres spéciales (dons, échanges, statiques)
- **Sprites** : PokéAPI `sprites/versions/generation-i` (red-blue, yellow)

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
- [x] Étape de génération de la base de données (`tools/`) dans la CI
- [ ] Générer un keystore de release et l'ajouter aux secrets GitHub (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`) — **à faire par toi**, voir le README
- [x] Workflow `release.yml` (sur tag `v*`) : build de l'APK release signé et publication dans **GitHub Releases**
- [x] Versionnage automatique (`versionCode` et `versionName` depuis le tag)
- [x] Documenter l'installation et les mises à jour via **Obtainium** (suivi des GitHub Releases sur GrapheneOS)
- [x] Publier l'APK debug comme artefact de workflow

## Phase 2 — Pipeline de données (`tools/`) ✅
- [x] Récupérer pret/pokered et pret/pokeyellow (commits figés, téléchargés par le script)
- [x] Parser les stats de base, types et CT/CS (`data/pokemon/base_stats/*.asm`)
- [x] Parser les évolutions et attaques par niveau (`data/pokemon/evos_moves.asm`), versions R/B et Jaune séparées
- [x] Parser les attaques (puissance, précision, PP, type)
- [x] Parser les rencontres sauvages (`data/wild/maps/*.asm`) : herbe, surf, cannes (Canne, Super Canne, Méga Canne), par version
- [x] Ajouter les rencontres spéciales : dons (Pokémon de départ, Évoli, Kicklee/Tygnon, Lokhlass…), échanges en jeu, Ronflex, oiseaux légendaires, Mewtwo, fossiles, Casino de Céladopole, Magicarpe vendu
- [x] Joindre les noms français depuis les CSV de PokéAPI (Pokémon, attaques, types, objets, descriptions)
- [x] Créer la table de traduction française des lieux (`tools/data/locations_fr.csv`)
- [ ] Parser les objets, dresseurs et warps (`data/maps/objects/*.asm`) — déplacé en phase 3, avec les coordonnées des cartes
- [x] Générer `pokedex.db` (schéma `tools/pokemaps_data/schema.sql`, à reproduire dans les entités Room en phase 4)
- [x] Tests de cohérence : 151 Pokémon, références valides, probabilités à 100 %, chaque Pokémon obtenable, aucun nom français manquant

## Phase 3 — Génération des cartes pixel-art
- [ ] Renderer : blocs et tilesets pret → PNG de chaque carte
- [ ] Assembler la carte du monde de Kanto (villes et routes reliées via les connexions de cartes)
- [ ] Générer les cartes intérieures (grottes, Tour Pokémon, Sylphe SARL, Manoir Pokémon, Parc Safari, Route Victoire, Caverne Azurée, bâtiments…)
- [ ] Découper chaque carte en tuiles pour MapCompose (niveaux de zoom, `nearest-neighbor` pour garder des pixels nets)
- [ ] Exporter les coordonnées (en pixels) de chaque lieu, zone d'herbe/d'eau, objet, PNJ et warp
- [ ] Intégrer les tuiles dans les assets de l'app (surveiller la taille de l'APK)

## Phase 4 — Squelette de l'app
- [ ] Mise en place de Hilt, Room (`createFromAsset`) et Navigation Compose
- [ ] Entités et DAO Room : `pokemon`, `type`, `evolution`, `move`, `pokemon_move`, `location`, `encounter`, `map_object`
- [ ] Repositories et cas d'usage
- [ ] Thème Material 3 (Material You et mode sombre)
- [ ] Sélecteur de version global (Rouge / Bleu / Jaune), mémorisé avec DataStore
- [ ] Barre de navigation : Carte / Pokédex

## Phase 5 — Pokédex
- [ ] Liste ou grille des 151 Pokémon (sprite, numéro, nom, types)
- [ ] Recherche par nom (FTS, accents ignorés : « evoli » trouve « Évoli ») et par numéro
- [ ] Filtres : type, disponible dans la version choisie
- [ ] Tests unitaires du ViewModel

## Phase 6 — Fiche Pokémon
- [ ] En-tête : sprite (selon la version), numéro, nom, types
- [ ] Stats de base (PV, Attaque, Défense, Vitesse, Spécial)
- [ ] Chaîne d'évolution cliquable (niveau, pierre, échange)
- [ ] Attaques par niveau (onglets R/B et Jaune)
- [ ] CT/CS compatibles
- [ ] Liste des lieux de capture (version, méthode, niveaux, taux)
- [ ] Bouton « Voir sur la carte »

## Phase 7 — Carte interactive
- [ ] Afficher la carte de Kanto avec MapCompose (zoom, déplacement, limites)
- [ ] Zones cliquables de chaque lieu
- [ ] Fiche en bas d'écran au clic : nom du lieu et Pokémon par méthode (herbe, surf, cannes), filtrés par version
- [ ] Accès aux cartes intérieures depuis les entrées (grottes, bâtiments, étages)
- [ ] Mode « surlignage » : lieux d'un Pokémon mis en évidence, avec recentrage automatique
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
- [ ] Table des types Gen 1 (avec ses bugs : Psy immunisé contre Spectre…)
- [ ] Calculateur de stats et DV
- [ ] Extension à Or/Argent/Cristal (Johto + Kanto)
