# Pokémaps

Application Android de **cartes interactives pour Pokémon Rouge, Bleu et Jaune**, entièrement en français :
carte de Kanto, Pokémon de chaque lieu, fiches Pokémon (évolutions, attaques, CT/CS) et Pokédex.

- Kotlin + Jetpack Compose, **Android 17 (API 37) minimum**
- **Aucun service Google Play** : l'application fonctionne sur GrapheneOS
- 100 % hors-ligne : toutes les données sont embarquées dans une base SQLite

Voir [plan.md](plan.md) pour la feuille de route.

## Structure

| Dossier | Contenu |
|---|---|
| `app/` | Application Android |
| `tools/` | Pipeline de données Python : génère `pokedex.db` |
| `tools/data/` | Données saisies à la main (noms français des lieux, dons et Pokémon fixes) |
| `.github/` | CI/CD (GitHub Actions) |

## Données

La base `pokedex.db` est générée par `tools/build_db.py` à partir de :

- [pret/pokered](https://github.com/pret/pokered) et [pret/pokeyellow](https://github.com/pret/pokeyellow),
  les désassemblages des jeux : statistiques, attaques, évolutions, rencontres sauvages, pêche, échanges, Casino…
- [PokéAPI](https://github.com/PokeAPI/pokeapi) (CSV) : noms français des Pokémon, attaques, types et objets,
  descriptions du Pokédex, tailles et poids
- `tools/data/*.csv` : noms français des 227 cartes du jeu, dons (Pokémon de départ, Évoli, Lokhlass…),
  fossiles et Ronflex

Les sources sont figées sur des commits précis (`tools/pokemaps_data/sources.py`), la génération est donc
reproductible. La base est vérifiée après chaque génération (151 Pokémon, références cohérentes, probabilités
de rencontre qui totalisent 100 %, chaque Pokémon obtenable…).

La base n'est pas versionnée : elle est générée par la CI, ou en local avec la commande ci-dessous.

## Compiler en local

Prérequis : JDK 21, Android SDK (API 37), Python 3.11 ou plus récent, git.

```bash
# 1. Générer la base de données (télécharge les sources dans tools/.cache)
python3 tools/build_db.py

# 2. Compiler et installer l'APK debug
./gradlew installDebug
```

Vérifications lancées par la CI :

```bash
./gradlew ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest   # Android
./gradlew ktlintFormat                                                    # corrige le style Kotlin

cd tools
pip install -r requirements-dev.txt
ruff check . && ruff format --check .   # style Python
python -m pytest                        # tests du pipeline
```

`checkNoGoogleServices` fait échouer la build si une dépendance tire les services Google Play
(`com.google.android.gms`), Firebase ou Play Core.

## CI/CD

- **CI** (`.github/workflows/ci.yml`), à chaque push et pull request : génération et tests de la base,
  ktlint, vérification sans Google Play, Android Lint, tests unitaires et APK debug
  (téléchargeable dans les artefacts du workflow pendant 14 jours).
- **Release** (`.github/workflows/release.yml`), à chaque tag `vX.Y.Z` : APK release signé publié dans
  [GitHub Releases](../../releases), avec son empreinte SHA-256.

### Publier une version

**Une seule fois** : créer la clé de signature et l'ajouter aux secrets du dépôt.

```bash
keytool -genkeypair -v -keystore pokemaps-release.jks -alias pokemaps \
  -keyalg RSA -keysize 4096 -validity 10000
base64 -w 0 pokemaps-release.jks > pokemaps-release.jks.base64
```

Dans GitHub, *Settings → Secrets and variables → Actions → New repository secret* :

| Secret | Valeur |
|---|---|
| `KEYSTORE_BASE64` | contenu de `pokemaps-release.jks.base64` |
| `KEYSTORE_PASSWORD` | mot de passe du keystore |
| `KEY_ALIAS` | `pokemaps` |
| `KEY_PASSWORD` | mot de passe de la clé |

⚠️ Conservez `pokemaps-release.jks` et ses mots de passe en lieu sûr, **hors du dépôt** : sans eux, il est
impossible de publier une mise à jour installable par-dessus l'application existante.

**À chaque version** :

```bash
git tag v1.0.0
git push origin v1.0.0
```

Le code de version Android est calculé à partir du tag : `MAJEUR × 10000 + MINEUR × 100 + CORRECTIF`.

## Installer sur GrapheneOS (Obtainium)

[Obtainium](https://github.com/ImranR98/Obtainium) installe et met à jour les applications directement
depuis leurs GitHub Releases.

1. Installer Obtainium (depuis ses GitHub Releases ou F-Droid).
2. *Ajouter une application* → URL : `https://github.com/sargo22341-prog/pokmaps`.
3. Obtainium installe la dernière version et signale les mises à jour.

Sans Obtainium : télécharger l'APK depuis la page Releases et l'ouvrir sur le téléphone.

## Mentions légales

Projet de fan, personnel et non commercial. Pokémon et les noms associés sont des marques de Nintendo,
Game Freak et The Pokémon Company. Ce dépôt ne contient aucune ROM ni ressource extraite d'une ROM.
Le code de l'application est sous licence [MIT](LICENSE).
