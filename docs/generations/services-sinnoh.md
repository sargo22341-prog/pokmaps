# Services et offres de Sinnoh

Les offres couvrent dons, œufs, échanges, boutiques selon les badges, tuteurs, soins, fossiles,
Pension, Casino, Maître des Capacités, baies et paillis. Les lectures suivent séparément chaque moteur.
Les prix, monnaies, conditions, quantités et paiements en Tessons sont conservés.
`npc_offer_component` distingue les composants remis ensemble et leur paiement unique.

Chaque offre possède exactement une attribution : événement posé ou scène avec case et déclencheur.
Le donneur réel peut différer du personnage qui démarre le dialogue, comme pour l'œuf d'Armand.
`npc_offers.csv` résout les attributions sans réécrire prix et quantités du moteur.

`story_events.csv` traduit chaque condition, y compris les conditions techniques sans texte visible.
Les états « pas encore reçu » et les drapeaux quotidiens restent distincts.
Les comparaisons de variables gardent leur provenance ; toute condition inconnue arrête l'export.
Les événements externes gardent leur mention explicite.

Les tests de parcours et `test_gen4_audit.py` confrontent les offres des trois cartouches aux données
livrées. Les catalogues `characters.json` gardent les événements bruts pour la relecture.
Voir les [lecteurs et données éditoriales](../donnees/pipeline.md#personnages-ds).
