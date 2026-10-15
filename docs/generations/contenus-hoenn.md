# Contenus propres à Hoenn

Rubis/Saphir et Émeraude disposent chacun de leur catalogue `app/src/main/assets/hoenn.json` :
43 baies, 354 attaques de Concours et 120 décorations. Rouge Feu/Vert Feuille n’exposent pas ces contenus.
Les plantations initiales restent dans la base Room : `new_game.inc`, événements de sol meuble,
offres `fruit_tree`, calque Baies et liens vers les fiches d’objet. La carte ne simule pas une sauvegarde.

Les données viennent de `pokeruby@5784633ce4ef` et `pokeemerald@731ad5bfd6e6` : `src/berry.c`,
`src/data/contest_moves.h`, `src/decoration.c` ou `src/data/decoration/header.h`.
Les formats positionnels de Rubis et les champs nommés d’Émeraude ont des lecteurs séparés.
Les 48 effets de Concours et les noms français des 120 décorations sont relus dans deux CSV éditoriaux :
`contest_effects_fr.csv` et `decorations_fr.csv`. Une traduction absente, vide ou répétée arrête l’export.
Les baies et les attaques conservent leurs noms PokéAPI français.

Les CSV PokéAPI `berries`, `berry_flavors`, `contest_effects` et `contest_combos` viennent du commit déjà
épinglé `bc92d3b6029e`. Les écarts sont conservés dans `comparison` : les propriétés GBA de pret
restent affichées, notamment les rendements qui diffèrent des données des jeux suivants.

Les fiches d’objet affichent durée d’étape, première récolte, rendement, cinq saveurs et onctuosité.
La Baie Enigma affiche ses propriétés par défaut avec une mention explicite pour les événements personnalisés.
Les fiches d’attaque Hoenn affichent catégorie, cœurs de charme et de blocage, effet et attaques préalables
aux enchaînements. Les attaques de combat et leurs effets sont conservés.

Cinq articles complètent chaque bibliothèque Hoenn : culture des baies, Concours et leurs salles par jeu,
Mélangeur et Parc Safari, recettes à deux avec une Baie Ceriz, Bases Secrètes et décorations.
Le guide donne les profils des 43 baies, y compris les baies rares absentes du catalogue d’objets Room ;
seules les fiches existantes reçoivent un lien. Les recettes utilisent les cinq saveurs de toutes les baies,
les soustractions circulaires, la pénalité des saveurs négatives, la moyenne entière d’onctuosité
et la vitesse du moteur. La liste affiche la base
avant vitesse ; les blocs noirs signalent leurs trois saveurs aléatoires, sans inventer le tirage.
L’appréciation selon la nature, la satiété et les usages au Safari sont expliqués dans le guide.

Les sources d’obtention des décorations reprennent les offres de `characters.json`, par version,
avec leurs chemins de scénario conservés. Les liens ouvrent les lieux correspondants.
Les tarifs restent dans leur monnaie : argent, jetons, cendres et Points Combat.
Les dons sont distingués des ventes, y compris les poupées du partenaire reçues au Casino.
Les articles rappellent les conditions des soldes, les récompenses et les distributions externes.
Une décoration sans boutique ou don dans les scripts est signalée comme obtention spéciale.
Il n’y a pas d’éditeur de Base Secrète ni de lecture de sauvegarde de cartouche.

Le catalogue séparé complète les données Room. Il est immuable une fois chargé,
lu sur `Dispatchers.IO` par le repository, borné à 512 Kio et validé avant son utilisation.
Les ViewModels et composables ne lisent pas les assets ; les textes de présentation viennent des ressources.
Les tests ordinaires utilisent l’asset versionné, les tests `pipeline` relisent les deux sources épinglées.

Génération ciblée : `python tools/build_data.py --hoenn-content-only`.
La génération complète et `--hoenn-maps-only` reconstruisent aussi ce catalogue et son inventaire SHA-256.
