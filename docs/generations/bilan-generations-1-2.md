# Bilan avant la génération 3

Bilan du 8 octobre 2026, fondé sur le code, les données générées et les tests du dépôt.
Il distingue les limites connues des fonctionnalités supplémentaires possibles ; il ne certifie
pas une relecture manuelle de toutes les cartes et de tous les scripts des six versions.

## Ce qui est déjà couvert

Rouge, Bleu, Jaune, Or, Argent et Cristal sont embarqués hors ligne. Les cartes, passages, objets,
équipes de dresseurs et offres des personnages sont générés à partir des sources épinglées.
Les statistiques, types, attaques et évolutions sont rattachés à leur génération ou groupe de versions.

La génération 2 couvre les trois moments, la pêche, le surf, Coup d'Boule, Éclate-Roc, les essaims,
le Concours, les objets tenus, les œufs, les chromatiques et les formes A à Z de Zarbi. Les lieux
possibles des Pokémon errants sont reliés aux cartes ; Cristal possède ses ajouts spécifiques.
Les tests vérifient notamment les tables de rencontres, leurs probabilités, les terrains,
les offres des personnages, les règles de capture et la concordance Room/SQLite.

## À fermer avant d'étendre les jeux

- **Outillage sans avertissement.** La validation Android réussit, mais l'environnement local émet
  des dépréciations Gradle (`Configuration.setVisible`) et JVM (`sun.misc.Unsafe`, ktlint et
  DataStore). Identifier l'origine et valider une combinaison d'outils compatible, sans suppression
  globale d'avertissements. Les changements de dépendances demandent une validation distincte.
- **Relecture visuelle des six versions.** Les validations structurelles ne prouvent pas que chaque
  entrée, objet, personnage et emplacement sauvage est visuellement bien placé. Revoir les variantes
  de Jaune, Johto et Kanto dans Or/Argent/Cristal, puis corriger les éventuels écarts dans `tools/data/`.
- **Conditions des scripts.** Le modèle des offres (`npc_offer`) ne représente pas de condition
  d'horaire, de jour ou de progression. Les rencontres gardent des conditions textuelles comme les
  essaims et le Concours, mais la liste n'est pas un simulateur de partie. Si le but est d'indiquer
  quand une offre devient disponible, il faut ajouter cette information et la vérifier contre pret.

## Compléments utiles, selon le périmètre souhaité

- **Capture plus précise, générations 1 et 2.** Le calculateur emploie un DV de PV moyen de 8.
  Une saisie des PV maximum réels ou du DV permettrait d'éviter cette approximation, déjà annoncée
  dans l'interface. La formule du domaine accepte un DV, mais l'écran ne propose pas ce réglage.
- **Guide de reproduction et de bonheur, génération 2.** Les groupes d'œufs, cycles, attaques par
  œuf et seuils d'évolution sont présents. Un outil de compatibilité des parents, d'héritage des
  attaques et un guide des gains de bonheur compléteraient les fiches ; ils ne sont pas implémentés.
- **Suivi des Pokémon errants, génération 2.** Les routes possibles sont disponibles ; il n'y a
  pas de suivi de leur position ou de leur déplacement au cours d'une partie.
- **Sauvegarde de collection.** Les captures et favoris sont mémorisés localement ; aucun parcours
  d'export/import utilisateur n'est proposé. Un format validé et versionné faciliterait leur transfert
  quand la collection couvrira davantage de générations.

Ces compléments ne sont pas des défauts de la carte actuelle. Ils doivent être choisis explicitement
avant de transformer l'application en guide de progression ou en simulateur de partie.
