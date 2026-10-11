# Services de Hoenn — phase 5

Les lecteurs des trois versions Hoenn alimentent `character_curation.json` de l'aperçu
`--gen3-curation-only`. Les sources sont les commits épinglés de `pokeruby` et `pokeemerald` ;
aucun changement des assets Android ni activation des jeux n'est nécessaire à cette préparation.
Le domaine Android et les ressources françaises prennent en charge les monnaies `money`, `coins`,
`battle_points` et `ashes`, ainsi que `daycare_egg`, `daycare_withdrawal` et `move_relearner`.
L’assemblage de ce catalogue dans la base embarquée reste l’étape suivante du plan.

## Offres relues

| Lieu | Contenu conservé |
|---|---|
| Devon, Mérouville | Lilia et Anorith au niveau 20, avec Fossile Racine ou Fossile Griffe requis |
| Pension, Route 117 | Dépôt, retrait à 100 ₽ + 100 ₽ par niveau gagné, œuf des parents compatibles |
| Casino de Lavandia | Cinq CT à 1 500, 3 500 ou 4 000 jetons, trois poupées à 1 000 jetons |
| Guichet du Casino | 50 jetons pour 1 000 ₽ et 500 pour 10 000 ₽ ; dons de jetons distincts |
| Atelier du Verre, Route 113 | Cinq flûtes à 250, 500, 500, 1 000 et 1 000 cendres ; chaise à 6 000 et bureau à 8 000 |
| Maître des Capacités, Autéquia | Une Écaille Cœur par capacité réapprise |
| Tuteurs ordinaires d'Émeraude | Capacités et drapeaux d'enseignement unique des scripts |
| Tuteurs de la Zone de Combat | Vingt capacités à 16, 24 ou 48 Points de Combat, selon la curation commune |
| Comptoirs de la Zone de Combat | 15 décorations à 16–256 PC, 6 vitamines à 1 PC, 9 objets tenus à 48 ou 64 PC |

Les espèces des œufs de la Pension dépendent des parents : le service `daycare_egg` ne devient pas
un don d'espèce fixe. Une place dans l'équipe est nécessaire. Rubis/Saphir exigent également une
place pour recevoir le fossile ranimé ; Émeraude peut l'envoyer au PC. Les chemins du script et
les appels C restent conservés, sans simuler les parents ou l'état d'une sauvegarde.

`required_item` distingue un fossile ou une Écaille Cœur requis de l'objet tenu par un Pokémon offert.
Les créations du verrier gardent le tarif de fabrication, y compris lorsqu'un sac ou PC plein a
différé la remise : la condition indique alors que le paiement a déjà eu lieu. Le Sac à Suie est
un don gratuit. Les décorations gratuites du Casino restent distinctes des lots achetés.

## Lecture et validation

`pret_hoenn_services.py` décrit les coûts à partir des instructions des scripts : `removecoins`,
`removemoney`, soustraction de `VAR_ASH_GATHER_COUNT` et prix de `VAR_0x8008` aux comptoirs.
Un tarif inconnu ou ambigu arrête la lecture. Les coordonnées, versions, provenance et chemins
alternatifs restent ceux de `pret_gen3_offers.py` ; les décorations reçues par `adddecoration`
et les jetons reçus par `addcoins` sont désormais conservés.

La relecture a révélé qu'un dialogue de confirmation pouvait garder la valeur du menu précédent
dans `VAR_RESULT`, ce qui masquait notamment le premier lot du Casino. L'analyse invalide désormais
la réponse aux dialogues oui/non, les résultats de vérification des décorations et la variable
écrite par `checkcoins`. Un test en mémoire couvre ce défaut.

Les tests vérifient les trois versions sur les sources locales épinglées, les objets requis,
les sept créations du verrier, les cinq CT, les trois poupées, les achats de jetons, la Pension,
le Maître des Capacités et les comptoirs et tuteurs de la Zone de Combat. Le parcours complet des
cinq versions dans l'export reste soumis aux contrôles de curation commune.
`require_resolved` continue de refuser les appels C non certifiés : cette préparation ne certifie
pas tous les effets du moteur et ne constitue pas l'assemblage des fiches Android.
