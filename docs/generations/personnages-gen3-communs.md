# Personnages et scripts GBA

Les cinq jeux GBA sont intégrés à la base distribuée. `maps_characters_gen3.py` assemble personnages et
équipes ; `maps_offers_gen3.py` traduit les conditions ; `maps_scenes_gen3.py` conserve les scènes automatiques.
`characters.json` garde les métadonnées et `trainers.json` décrit les équipes dans l’aperçu dédié.
Les commandes ciblées sont dans le [pipeline](../donnees/pipeline.md#génération-ciblée).

## Lecture des scripts

`Gen3PretRepo.offers[version].read(label)` lit un script seul ; `read_object(event)` applique d’abord
la condition de présence de l’objet. Dons, boutiques, échanges, services, tuteurs et conditions gardent
versions, coordonnées, provenance et chemins alternatifs. Appels et retours conservent variables et contexte ;
les contradictions sont écartées. Parcours et profondeur sont bornés ; une référence absente provoque une erreur.

`ScriptOffers.unresolved` garde les expressions C calculées ; `specials` recense les appels C.
`require_resolved` refuse une expression ou un appel non certifié, même si aucune offre n’a été trouvée.
La propagation des écritures C invalide les anciennes valeurs susceptibles de cacher une branche ;
elle ne simule pas le moteur C.

| Curation dans `tools/data/` | Rôle |
|---|---|
| `npc_duplicates.csv` | Écarter les acteurs répétés d’une même scène |
| `scene_actors_gen3.csv` | Rattacher combats et dons à leur acteur ; `only` restreint les offres d’une scène commune |
| `npc_offers.csv`, action `resolve` | Décrire les résultats possibles d’une expression C relue |
| `story_events.csv` | Traduire drapeaux et comparaisons numériques (`operator,value,phrase`) |

Une comparaison non relue arrête sa traduction. Les résultats aléatoires (loterie, baies, quiz, Pyramide)
sont des possibilités, sans probabilité inventée. `gift_custom_item` représente un objet choisi par un joueur.
`character_curation.json` conserve positions, raisons d’exclusion et offres ; une correction inutilisée est refusée.
Les graphismes `OBJ_EVENT_GFX_VAR_*` sont résolus à l’assemblage, sans leur attribuer arbitrairement un nom fixe.

## Équipes, revanches et objets

Les attaques initiales suivent `GiveBoxMonInitialMoveset` : ordre, doublons et remplacement de la plus ancienne
après quatre attaques. Les équipes explicites gardent leurs emplacements `MOVE_NONE`. IV source converti
par `iv * 31 // 255`, zéro si omis. Les variantes du rival et les combats doubles restent distincts.
Les rangs de revanche gardent les trous `SKIP`, répétitions et conditions ; le rang zéro n’est pas toujours
le premier combat scénarisé (exemple : Timmy à la Route Victoire).

Rubis/Saphir : PokéNav, cinq badges, 255 pas et tirage de 31 %. Émeraude distingue appels à distance et
revanches des Champions. Les remakes suivent les étapes de scénario du Cherche VS. Les tests relisent
les routines du moteur ; attaques, objets ou progressions inconnus sont refusés.

`pret_gen3_items.py` lit objets ramassables et cachés ; `maps_items_gen3.py` les projette sur les plans,
marées et Mirage. `map_items.json` conserve quantités, élévations, scripts, drapeaux et `underfoot`,
y compris les jetons cachés du Casino. Les Balls contenant un Pokémon ou appartenant au décor ne sont pas des objets.

Les [services Hoenn](services-hoenn.md) et [services des remakes](services-remake-1g.md) détaillent les coûts
et objets requis. Les noms français viennent des CSV éditoriaux ; toute absence ou ambiguïté arrête l’export.

## Déblocage du Pokédex National relu

Les trois groupes gardent `national_dex=True` : ils proposent le National de 386 espèces en plus du régional.
L'application n'est pas synchronisée avec la sauvegarde du jeu ; les conditions décrivent le déblocage dans le jeu.

- **Émeraude** : la première entrée au Panthéon met `VAR_DEX_UPGRADE_JOHTO_STARTER_STATE` de 0 à 1
  (`data/scripts/hall_of_fame.inc`). Dans le laboratoire de Seko, le script de trame sélectionne alors
  `UpgradeToNationalDex`, active le National et passe la variable à 2. Aucun nombre d'espèces capturées n'est requis.
- **Rouge Feu/Vert Feuille** : le dialogue de Chen vérifie `FLAG_SYS_GAME_CLEAR`, puis au moins 60 espèces
  capturées et `FLAG_WORLD_MAP_ONE_ISLAND`. L'évaluation renseigne `VAR_0x8009` avec le nombre de captures
  de Kanto (`data/scripts/pokedex_rating.inc`). La scène automatique au retour du Panthéon vérifie également
  les captures et la visite à l'Île 1 (`data/maps/PalletTown/scripts.inc`). Les Îles 4 à 7 ne sont pas nécessaires.
- **Rubis/Saphir** : après un échange, `sub_804BA94` appelle `sub_804BA64` si le partenaire est connecté.
  Cette routine active le National quand `gLinkPlayers[mpId ^ 1].lp_field_2 == 0x8000` (`src/trade.c`).
  Émeraude et Rouge Feu/Vert Feuille transmettent ce marqueur dans `src/link.c` ; Rubis/Saphir transmettent 0.
  La routine ne teste ni l'espèce reçue ni la victoire à la Ligue. Un échange autorisé avec ces partenaires
  peut donc activer le National même si l'espèce appartient au Pokédex de Hoenn. Les restrictions d'échange
  du jeu partenaire continuent de s'appliquer. Le don événementiel peut aussi l'activer
  (`src/mystery_event_script.c`, `MEScrCmd_givenationaldex`).

Les tests `test_gen3_national_dex.py` vérifient les déclencheurs et marqueurs dans les sources épinglées.
