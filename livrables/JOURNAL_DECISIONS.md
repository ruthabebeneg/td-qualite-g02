# Journal des décisions

Une ligne par décision de seuil, de sévérité, de définition ou de règle de survie. Une décision sans rôle ni justification chiffrée n'est pas une décision. Ce journal alimente la partie « La décision » du dossier go/no-go.

À documenter selon les travaux effectivement réalisés : définition CD-001 et date métier du lot ; regex et populations applicables ; convention de sentinelle ; correction de statut proposée puis validée ; seuils et zones de rapprochement ; survie des attributs ; écarts à la cible BAN ; couverture et limites du certificat. Les exemples du support ne sont pas des décisions de notre groupe. Tant qu’une validation manque, identifier le choix comme proposition et ne pas inventer de signataire. Les preuves Python se trouvent dans les notebooks de séance, avec leurs cellules exécutées et résultats.

| N° | Date | Séance | Règle ou objet | Décision (ce qui est arrêté) | Justification chiffrée (preuve) | Rôle décideur | Alternative écartée |
|---|---|---|---|---|---|---|---|
| 1 | … | … | … | … | … | … | … |
| 2 | … | … | … | … | … | … | … |
| 3 | … | … | … | … | … | … | … |
| 4 | … | … | … | … | … | … | … |
| 5 | … | … | … | … | … | … | … |
| 6 | … | … | … | … | … | … | … |
| 7 | … | … | … | … | … | … | … |
| 8 | … | … | … | … | … | … | … |

Ajoutez des lignes autant que nécessaire. Exemples de décisions attendues : sévérité d'une règle, seuil d'avertissement, définition unique du client actif, convention de la valeur sentinelle, seuils de rapprochement, règle de survie par attribut, seuil de la porte G.

## S2 — Propositions soumises au Data Owner le 2026-10-23

Ces références P-S2 ne sont pas des décisions approuvées. Date de décision,
identité du titulaire et validation : **[À COMPLÉTER]**. Preuves : sorties enregistrées de
[US-10](../notebooks/S2_US10_regles_en_tests.ipynb), cellules 6 à 17,
et [US-11](../notebooks/S2_US11_lignes_en_echec.ipynb), cellules 1 à 4
(numérotation à partir de zéro), disponibles sur `main` au commit `2ed45af`.
Lot déclaré dans US-10 : `L-2026-10-01`, couche BRONZE.
Les tests n'ont pas été rejoués pour cette analyse ; la date de leur exécution
reste à confirmer. Les sorties consultées ne démontrent pas l'historisation.

| Référence | Objet | Proposition à valider | Justification chiffrée / preuve | Rôle décideur | Alternative examinée et limite |
|---|---|---|---|---|---|
| P-S2-01 | RQ-001/002/009/010/020 | Maintenir les propositions BLOQUANTE, 100 % du catalogue ; réserve sur populations et clés | US-10 : 800 / 8 426 / 120 / 600 échecs ; zéro pour deux clés techniques seulement | Data Owner, validation en attente | Abaisser les seuils à la qualité reçue masquerait les défauts ; aucune alternative arrêtée |
| P-S2-02 | RQ-003/005 | Maintenir les propositions AVERTISSEMENT, 98 % ; analyser le contact et les pays exclus | US-10 cellules 9–10 et 16 : 5 995/49 978 et 1 478/97 037 ; écarts −10,00 et +0,48 points | Data Owner, validation en attente | Blocage systématique à comparer aux moyens alternatifs et à l'impact ; non arbitré |
| P-S2-03 | RQ-002 / US-13 | Âge révolu au début du contrat pour le souscripteur physique ; cas indéterminés séparés | US-10 cellule 8 : 8 426 échecs composites ; comparaison aujourd'hui et cas réel manquants | Data Owner, validation en attente | Âge actuel ne démontre pas l'âge à la souscription ; preuve comparative à fournir |
| P-S2-04 | US-11 | Prioriser l'analyse des bloquantes puis les actions de contact et d'adresse ; aucun changement manuel de bronze | US-10 cellule 17 : 17 419 occurrences ; US-11 cellule 4 : échantillon 7/7/6 limité à trois RQ | Data Owner, validation en attente | Assimiler les occurrences à des clients distincts ou extrapoler l'échantillon serait injustifié |
| P-S2-05 | US-15 | Moyenne simple par règle/table, conserver pires règles et écarts ; conclusion limitée aux sorties reçues | Recalcul documenté : 100,00 / 88,00 / 97,33 / 99,20 % ; aucune preuve dq_history | Data Owner, validation en attente | Moyenne globale et conformité exhaustive non justifiées par ces huit résultats |

### Calcul de la synthèse proposée (P-S2-05)

Le taux de chaque mesure est `100 × (testées − échecs) / testées`.
La moyenne par dimension donne le même poids à chaque couple règle/table ;
l'arrondi à deux décimales intervient après le calcul.

| Dimension | Effectifs utilisés (testées, échecs) | Taux moyen recalculé |
|---|---|---|
| Unicité | RQ-020 client (100 000, 0) et contrat (100 000, 0) | 100,00 % |
| Complétude | RQ-003 client (49 978, 5 995) | 88,00 % |
| Validité | RQ-002 contrat (100 000, 8 426), RQ-005 client (97 037, 1 478), RQ-009 client (100 000, 120), RQ-010 contrat (100 000, 600) | 97,33 % |
| Cohérence | RQ-001 contrat (100 000, 800) | 99,20 % |

Ces moyennes ne représentent pas une proportion de clients sans défaut et
ne compensent pas une règle bloquante en échec. Les 8 426 échecs de RQ-002
mêlent potentiellement âge, statut et dates non évaluables. RQ-020 vérifie
`bronze_row_id` sur deux tables seulement. La couverture complète reste à
justifier. Aucun certificat GO ni engagement humain ne découle de ce tableau.
