# Personnages et scripts de Sinnoh

Les scripts macros de Platine et les scripts compilés de Diamant/Perle sont ramenés à des étapes
communes par `pret_gen4_flow.py`. Le désassembleur suit les points d'entrée et refuse les commandes
inconnues ; les valeurs et chemins restent bornés. Les drapeaux et variables conservent leur origine.

`pret_gen4_trainers.py` lit équipes et attaques par défaut ; `pret_gen4_battles.py` rattache les
combats posés et de scénario aux personnages. Les variantes de starter et sexe restent distinctes.
`pret_gen4_rematches.py` lit les équipes du Cherche VS et leurs conditions.
`pret_gen4_national_dex.py` contrôle le déblocage du National dans chaque moteur.

Les événements gardent coordonnées, apparence, script, drapeau de retrait et identifiant local.
Les poses alternatives peuvent partager un repère sans fusionner les événements source.
Les figurants temporaires sont annotés dans `npc_duplicates.csv` ; les noms français viennent des
CSV de classes, personnages et services. Une annotation inconnue ou inutilisée bloque la génération.

Les objets visibles et cachés conservent position, quantité et drapeau. Les lots sont annotés dans
le nom du repère, sa fiche et la liste du lieu. Les tests d'audit confrontent chaque objet et équipe
aux sources, après translation des assemblages. Voir le [pipeline](../donnees/pipeline.md#personnages-ds).
