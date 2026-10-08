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

- **Outillage : analyse terminée, avertissement AGP toujours présent.** Gradle utilise Temurin 21
  comme la CI (`gradle/gradle-daemon-jvm.properties`) : les avertissements `sun.misc.Unsafe` de
  ktlint et DataStore ont disparu. `Configuration.setVisible` vient d'AGP lui-même ; l'origine et
  les versions examinées sont documentées dans le README. Aucun avertissement n'est masqué.
  Ce point reste à surveiller lors des mises à jour d'AGP ; le dépôt n'est donc pas déclaré sans
  avertissement d'outillage.
- **Relecture visuelle restante : terminée sur les rendus générés du PC.** Les six assemblages
  du monde ont été examinés : Kanto de Rouge/Bleu et de Jaune, Johto et Kanto d'Or/Argent et de
  Cristal. Les 796 positions d'entrées de ces assemblages ont été revues sur des extraits agrandis,
  marqueur superposé au décor, sans nouvel écart confirmé. Les plans de Rouge/Bleu et d'Or/Argent
  sont communs aux deux versions de chaque groupe.
  Les cas signalés par l'audit des cases infranchissables sont légitimes : les 16 objets des salles
  des Ruines d'Alpha de Cristal sont sur des socles ; l'institutrice et le Persian du Parc Naturel,
  le capitaine du M/S Aquaria et la Pokéfan du Centre Pokémon de Doublonville sont assis ; le vendeur
  du toit du Centre Commercial est derrière son étal. Ils restent aux coordonnées de pret.
  Le sbire des caméras du repaire d'Acajou est en revanche écarté dans `npc_duplicates.csv`, avec
  un test sur Or/Argent et Cristal : le callback le masque, puis chaque alarme le déplace avant son
  apparition ; il n'est jamais visible en (0, 0). Les corrections antérieures des emplacements
  sauvages de Jaune et des 76 superpositions, leur validation à la génération et l'écartement des
  marqueurs de personnages qui partagent une case restent en place. Cette passe complète les
  contrôles déjà faits sur téléphone ; elle ne constitue pas une nouvelle passe sur téléphone ni
  une certification de chaque intérieur et de chaque état du scénario.
- **Conditions des offres : terminé.** Les offres des six jeux affichent leurs jours, moments et
  étapes du scénario dans la fiche du personnage. L'analyse suit les chemins des scripts pret et
  la présence du personnage ; les 83 drapeaux rencontrés sont relus dans `story_events.csv`.
  La CT12 impossible de Cristal est retirée et les labels locaux sans deux-points sont lus.
  Limite explicite : les tests des routines du moteur, hors scripts de carte, ne sont pas analysés
  (par exemple le Pokédex exigé par l'hôtesse du Club Link de la première génération). Le README
  décrit ce périmètre ; la liste des offres reste un guide et ne simule pas une sauvegarde.

## Compléments utiles, selon le périmètre souhaité

- **Guide de reproduction et de bonheur, génération 2.** Les groupes d'œufs, cycles, attaques par
  œuf et seuils d'évolution sont présents. L'onglet Guides ajoute un outil de compatibilité des parents
  (groupes, sexes et DV), une simulation des quatre attaques à l'éclosion à partir des attaques cochées
  des parents et un calculateur des gains et pertes de bonheur selon les seuils du jeu.
- **Suivi des Pokémon errants, génération 2.** L'onglet Guides conserve le dernier lieu observé
  de Raikou, Entei et, dans Or/Argent, Suicune. Les routes proposées suivent pret et sont reliées à la carte.
  Le suivi est manuel ; il ne prédit pas un déplacement et ne lit pas la sauvegarde du jeu.
- **Sauvegarde de collection.** Les Réglages proposent un export/import JSON versionné et validé,
  qui fusionne captures par version, favoris, étapes de guide et observations des Pokémon errants.
  Les clés API, connexions et autres réglages sont exclus.

Ces compléments ont été demandés explicitement, ainsi que les soluces, quêtes annexes, événements hebdomadaires,
astuces, glitches et 519 succès traduits. Une connexion facultative RetroAchievements lit uniquement
la progression, sur demande ; le suivi manuel et les guides restent utilisables hors ligne.
