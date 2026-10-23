# Personnages, objets et services HGSS — phase 5

Les trois volets 5A, 5B et 5C sont implémentés dans le pipeline préparatoire.
La génération complète convertit désormais les acteurs utiles, équipes, revanches, objets et offres
vers les tables communes Android. L’aperçu séparé reste disponible pour la relecture.
Les services de scène sans attribution certaine à un personnage sont détaillés dans les guides,
sans fabriquer de repère ni attribuer leurs cadeaux à tous les personnages du lieu.

## Générer et consulter

Les prérequis des phases 1–4 doivent être présents dans `tools/build/preview`.
Aucun téléchargement ni accès à une ROM n'est nécessaire lorsque les sources épinglées sont préparées.

```powershell
python tools/build_data.py --hgss-characters-only
python tools/check_assets.py --hgss-characters tools/build/preview/hgss-characters
python -m pytest -q -m pipeline tools/tests/test_hgss_character_sources.py tools/tests/test_hgss_character_catalog.py
```

Ouvrir `tools/build/preview/hgss-characters/index.html` : recherche des personnages par nom ou lieu,
équipes, liens vers les planches de placement, rendez-vous, objets et catalogues de services.
L'aperçu fonctionne directement sur disque, sans serveur ni ressource distante.
`characters.json` conserve les données structurées et les instructions natives ; `inventory.json`
couvre chaque sortie, y compris les images et la page HTML. Une génération invalide ne remplace pas l'aperçu précédent.

## 5A — Acteurs et combats

- 497 banques de scripts de terrain, 2 392 acteurs et 194 déclencheurs de scène conservés avec leur provenance.
- 737 équipes : espèces, niveaux, formes, objets, attaques explicites ou calculées depuis les listes HGSS.
- 123 commandes de combats locaux résolues, avec variantes corrélées au starter, sexe et jeu lorsque le script les lit.
- Adversaires et partenaires distingués ; chaque équipe de scène possède un acteur et un lieu vérifiés.
- 762 acteurs utiles, 100 sprites décodés, 39 planches de placement : coordonnées et hauteur BDHC natives,
  projection de l'atlas, coupes inférieures lorsqu'une surface supérieure masque le personnage.
- Les positions d'attente de six acteurs de scène sont remplacées dans l'affichage par une position de scène
  documentée ; les coordonnées originales et les autres positions de script restent consultables.
- Copieuse et quatre déguisements de Parmanie : alias explicites pour conserver un seul repère par interaction.
- Trois décalages d'affichage écartent deux repères de passages et ramènent le rival sur le bord visible de Ville Griotte.

Le décodage des accompagnateurs statiques choisit explicitement la palette normale et la texture de face.
À la frontière Ville Griotte/Route 29, la position du rival est hors du bloc BDHC de ville :
sa hauteur nulle vient de l'événement et de `MovePersonFacing`, sans hauteur inventée.
Les personnages nommés et classes portent des libellés français ; les noms individuels natifs sont conservés
avec les équipes. Les drapeaux de masquage ne sont pas supprimés : un acteur conditionnel n'est pas présenté
comme présent simultanément avec toutes ses variantes.

## 5B — Pokématos et calendrier

75 contacts et 63 séries natives de six emplacements. La sélection cherche la première équipe non vaincue,
puis applique le repli natif si le groupe est verrouillé, en respectant les sentinelles.
Les groupes se débloquent après la Tour Radio, le Panthéon puis Blue.

Les 16 champions ont leur jour et leur période d'appel, leurs sites d'enregistrement et les chemins de présence
qui lèvent leur drapeau de masquage. Les conditions du rendez-vous comprennent le numéro enregistré,
les seize Badges, l'appel hors du lieu du contact et l'absence de rendez-vous déjà actif ; destination : Dojo de Safrania.
Matin : 4–10 h ; journée : 10–20 h ; nuit : 20–4 h.
Les huit en-têtes entrants et sortants de chaque contact conservent ordre, chance et conditions natives.
Ces tests conditionnels ne constituent pas une probabilité globale ni une prédiction d'appel.

Les cinq salles de la Ligue distinguent équipe initiale et renforcée : seuil de huit Badges de Kanto,
lu dans la variable de scénario, sans condition inventée sur Red. Aucun mécanisme du Cherche VS n'est repris.

## 5C — Objets, offres et services

- 497 objets placés, visibles ou cachés, avec quantité et script de collecte.
- 567 offres résolues : dons, achats, Pokémon, prêts, échanges, capacités, Sceaux, Rubans et enregistrement téléphonique.
- Argent, Jetons, Points Combat, Points Athlète et objets consommés restent des contreparties distinctes.
- 19 articles ordinaires avec paliers de Badges, 30 stocks spéciaux ; Pokéathlon : 14 stocks jour/Pokédex National,
  27 Cartes Mémo et limite quotidienne ; Sceaux : sept stocks de sept articles à 100 unités monétaires chacun.
- 31 arbres à Noigrumes et sept transformations : même quantité en entrée et sortie, remise le lendemain
  par réinitialisation quotidienne, sans inventer un délai de 24 heures.
- 52 capacités de tuteurs, dont Coup d'Boule gratuit, plus les capacités enseignées par les scripts locaux.
  Réapprentissage : une Écaille Cœur après réussite ; Pension : `100 × (niveaux gagnés + 1)` au retrait.
- 13 échanges ; sept fossiles rendus au niveau 20 après sortie et retour dans le bâtiment.
- Achats de la mère : neuf seuils normaux, dix-sept lots de cinq Baies, débit de l'épargne et file de cinq livraisons.
- Cartes à gratter : un Point Combat pour trois cartes, vingt-trois lots de trois Baies ou une Pépite,
  récompense déterminée par le résultat du mini-jeu natif ; aucun tirage simulé.
- Cadeaux téléphoniques : quantité et candidats natifs ; les distributions externes restent signalées comme conditionnelles.

Les quantités dépendant d'un dépôt ou du stock de Sceaux sont des règles explicites, testées aux limites.
Les prédicats locaux des offres et leurs scripts complets restent associés : les chemins rejoignant une même
commande ne sont pas transformés en une condition de scénario unique inventée.

## Provenance et vérification

Source native : `pret/pokeheartgold`, commit `6988158691eb6178cff697cda0428045ddcba5fb`.
Le [contrat des sources](personnages-hgss-sources.json) épingle 2 416 fichiers natifs et dix CSV PokéAPI
pour les libellés. Les recettes et CSV éditoriaux sont également empreintés dans l'aperçu.
Les fichiers `tools/data/hgss_*names.csv`, `hgss_battle_*.csv`, `hgss_actor_curation.csv` et
`hgss_scene_placements.csv` portent leur provenance ; aucune retouche n'est cachée dans une sortie générée.

La [preuve de génération](personnages-hgss-preuve.json) fixe les comptes et empreintes relus.
La validation refuse toute offre non résolue, équipe absente, attribution incomplète, sprite manquant,
placement hors image, recette périmée ou inventaire altéré. Les parcours de flux et chemins ont des plafonds explicites.
Les tests ordinaires couvrent les règles pures ; les tests `pipeline` relisent les sources et l'aperçu généré,
sans réseau. Les assets des quatorze jeux distribués restent vérifiés séparément.
