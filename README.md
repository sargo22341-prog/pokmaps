# Pokémaps

Application Android en français : cartes interactives, Pokédex et guides pour **Rouge, Bleu, Jaune,
Or, Argent, Cristal, Rubis, Saphir, Émeraude, Rouge Feu et Vert Feuille**.

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
Les guides regroupent soluces, quêtes, astuces et succès officiels traduits.

Captures, formes de Zarbi et progression sont mémorisées localement. Les Réglages proposent
la portée des captures, les animations, la sauvegarde JSON et la connexion RetroAchievements.
L’application ne lit aucune sauvegarde de cartouche et ne prédit aucun tirage du jeu.

| Carte | Pokédex | Fiche Pokémon |
|---|---|---|
| ![Carte][carte] | ![Pokédex][pokedex] | ![Pikachu][pokemon] |

[carte]: docs/screenshots/carte.webp
[pokedex]: docs/screenshots/pokedex.webp
[pokemon]: docs/screenshots/pokemon.webp

## Documentation

Lire [AGENTS.md](AGENTS.md) avant toute modification, puis uniquement les pages utiles à la tâche
via [l’index](docs/README.md).

| Besoin | Référence |
|---|---|
| Compiler, vérifier, installer en debug | [Développement](docs/developpement.md) |
| Sources, génération et éditeur de cartes | [Pipeline](docs/donnees/pipeline.md) |
| Fonctionnement des écrans | [Documentation fonctionnelle](docs/README.md#fonctionnement) |
| Particularités des jeux | [Générations](docs/README.md#jeux-et-règles) |
| Mesurer une optimisation | [Performances](docs/performance.md) |

`app/` contient l’application ; `tools/` le pipeline Python ; `tools/data/` les données éditoriales.
Les assets finaux et leur inventaire SHA-256 sont versionnés. Les builds Android les réutilisent
sans génération ni téléchargement de contenu Pokémon. Les sources brutes et caches restent hors Git.
Les sources principales sont PokéAPI, PokeAPI/sprites, pokesprite et les dépôts pret ; aucune ressource
n’est récupérée sur pokemaps.net. Leur rôle est détaillé dans le pipeline.

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
