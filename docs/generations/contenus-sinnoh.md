# Contenus propres à Sinnoh

Diamant et Perle utilisent `pret/pokediamond`, Platine `pret/pokeplatinum`, aux commits de
`tools/pokemaps_data/sources.py`. Chaque moteur est lu séparément. Les tests de sources comparent
les données communes ; aucune règle de Hoenn ne remplace une règle DS.

## Catalogue hors ligne

`python tools/build_data.py --sinnoh-content-only` produit `app/src/main/assets/sinnoh.json` et
actualise l’inventaire SHA-256. La génération complète appelle aussi ce générateur. Le catalogue
ne modifie pas le schéma Room ; il est validé par `tools/check_assets.py` sans cache ni réseau.
Les fichiers `contest_effects_gen4_fr.csv`, `underground_goods_fr.csv`, `underground_traps_fr.csv`
et `natures_fr.csv` portent les traductions éditoriales. Les noms Pokémon, attaques et objets
proviennent des CSV PokéAPI épinglés. Les numéros d’objets des équipes sont ceux du moteur DS,
convertis par `item_game_indices` de génération 4 pour leur nom français.
La [liste française des décorations](https://www.pokepedia.fr/D%C3%A9coration#Dans_Pok%C3%A9mon_Diamant,_Perle_et_Platine)
sert à relire les noms du mobilier ; les chiffres et conditions restent ceux des moteurs épinglés.

`SinnohRepository` charge le catalogue sur le dispatcher IO, avec une limite de deux Mio,
valide ses identités et intervalles, puis conserve les deux groupes en mémoire. Une lecture
ou donnée invalide provoque l’état d’erreur de la fiche ou des guides. Les autres générations
n’ouvrent pas ce fichier. Les cas d’usage et le repository des attaques conservent le sens
de dépendance des couches ; les composables reçoivent uniquement les modèles validés.

## Baies, paillis et Poffins

Les 64 baies sont lues dans `res/items/data/*_berry.json` de Platine et
`files/itemtool/itemdata/nuts_data.json` de Diamant/Perle. Les plantations initiales restent
issues de `include/data/berry_init.h` et de l’overlay 52 ; leurs marqueurs et offres appartiennent
au calque des fruits déjà distribué.

Les règles de croissance sont dans `src/berry_patches.c` et `arm9/asm/unk_020250A4.s` :
quatre stades jusqu’aux fruits, rendement de base multiplié par la qualité (maximum 5),
récolte minimale de deux baies, humidité restaurée à 100 par l’arrosage. Fertipousse multiplie
la durée par trois quarts et augmente la perte horaire de moitié ; Fertihumide augmente
la durée de moitié et divise la perte par deux. Les divisions restent entières, dans l’ordre
du moteur. Fertistable prolonge les fruits de quatre à six stades ; Fertiglu porte les
repousses de dix à quinze cycles.

Les cinq saveurs et la douceur sont celles des ingrédients pour Poffins. La fiche et le guide
expliquent leur relation aux conditions de concours. Le mini-jeu, les brûlures, débordements,
temps de cuisson et baies d’autres joueurs ne sont pas simulés ; aucun niveau final n’est promis.

## Super Concours

Les 467 attaques jouables sont lues dans `res/moves/*/data.json` et
`files/poketool/waza/waza_tbl.json`. Les trois emplacements techniques après la dernière
attaque de Diamant/Perle sont vérifiés et exclus. Catégories et effets sont propres aux
Super Concours. Les 23 effets définis sont traduits ; l’effet numéro 3 n’est utilisé par
aucune des 467 attaques. L’attrait de base vient de `src/unk_02094EDC.c` pour Platine et de
la table à enregistrements de 26 octets dans `arm9/asm/unk_020828BC.s` pour Diamant/Perle.

## Souterrain

`src/underground/mining.c` et l’overlay 18 de Diamant/Perle fournissent 85 orientations
d’objets et obstacles. Les orientations sont regroupées en 58 entrées d’objets ; les rochers
ne deviennent pas des trésors. Les quatre poids gardent leur sens : Diamant/Perle, avant/après
le National ; ou identifiant impair/pair, avant/après le National dans Platine. Ce sont des
poids de sélection de base, pas des chances de réussir une fouille. Les progrès souterrains
peuvent en outre augmenter les poids de certaines sphères dans Diamant/Perle.

Les 132 entrées de mobilier et 27 pièges vendables sont lus séparément dans `src/goods.c`,
`src/underground/trap_prices.c`, `arm9/asm/unk_0204CA80.s` et l’overlay 18. Les catalogues
conservent les dimensions, montants, monnaies et exigences du National. Pour les prix en sphères,
la borne supérieure du moteur est exclue ; l’interface affiche donc `maximum - 1`.
Les stocks ne sont pas prédits. Les entrées de base et décorations explicitement inutilisées
ne sont pas présentées comme récompenses ordinaires.

Les lieux d’obtention distinguent marchands souterrains, Centre Commercial de Voilaroc,
Homme du Souterrain à Vestigion, décorateur d’Unionpolis et trophées de la Tour. La Poupée Lucario
est un cadeau externe ; aucun vendeur ordinaire n’est inventé. Les données de distribution sont
également recensées dans le [catalogue Serebii](https://www.serebii.net/itemdex/lucariodoll.shtml).
Les quêtes et la décoration des bases sont décrites, sans simulation du multijoueur ni lecture de sauvegarde.

## Installations de combat

La Tour conserve les 950 configurations de chacun des deux moteurs : JSON ordonnés de
`res/trainers/frontier/` ou membres binaires `files/battle/b_tower/{btdpm,btdtr}`.
Les listes de dresseurs renvoient aux configurations ; les séries regroupent les configurations
possibles, sans énumérer de fausses équipes garanties. Les plages de la Tour sont inclusives.
Ses deux groupes par série distinguent les six premiers combats et le septième. À partir de
la huitième série, le dernier groupe est réutilisé. Koner possède deux équipes fixes séparées.

Dans Platine, le Castel, l’Arcade et l’Usine utilisent une borne supérieure de dresseur exclue.
Leurs lecteurs suivent `src/overlay104/battle_*_helpers.c`. Le Castel et l’Arcade réutilisent
les configurations de la Zone ; les objets affichés sont ceux de la configuration source,
l’installation pouvant les retirer ou les remplacer pendant le défi.

L’Usine distingue location au niveau 50, location en niveau libre et adversaires en niveau libre.
Le choix adverse dépend du dresseur et peut donc changer au septième combat. Les réserves
améliorées, IV et seuils d’échanges sont conservés. Les réserves particulières de Cardus aux
combats 21 et 49 sont listées séparément des équipes fixes des autres meneurs.

La Scène lit ses 477 configurations dans `res/prebuilt/battle/b_pl_stage/pl_bsdpm.narc`.
Les dix rangs gardent leurs bornes de groupes, puis le moteur filtre selon le type et l’espèce
engagée. Argenta tire dans le groupe de l’espèce du joueur au combat 50, et dans le dernier
groupe au combat 170. Aucun parcours, tirage de configuration ou résultat de roulette n’est simulé.
