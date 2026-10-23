# Journal des décisions

Ce journal rassemble les choix proposés pour S2 et les résultats qui les motivent.
Il doit rester cohérent avec le PowerPoint du groupe.

## S2 — Analyse du 23 octobre 2026

Pour S2, le travail du Data Owner consiste à examiner les résultats, proposer
les seuils à retenir et expliquer les conséquences des anomalies pour le métier.
Les choix présentés ici restent des propositions : leur validation n'est pas
consignée à ce stade.

L'analyse s'appuie sur les sorties enregistrées dans les notebooks
[US-10](../notebooks/S2_US10_regles_en_tests.ipynb), cellules 6 à 17,
et [US-11](../notebooks/S2_US11_lignes_en_echec.ipynb), cellules 1 à 4.
Les cellules sont comptées à partir de zéro. Ces fichiers sont disponibles
sur `main` au commit `2ed45af`.
Lot déclaré dans US-10 : `L-2026-10-01`, couche BRONZE.
Les tests n'ont pas été rejoués pour cette analyse ; la date de leur exécution
reste à confirmer. Les fichiers consultés ne montrent pas l'enregistrement des résultats dans `dq.dq_history`.

| Référence | Règles concernées | Choix proposé | Pourquoi ce choix ? | Rôle chargé de valider | Autre possibilité examinée |
|---|---|---|---|---|---|
| P-S2-01 | RQ-001, RQ-002, RQ-009, RQ-010 et RQ-020 | Garder le seuil proposé de 100 % et la sévérité bloquante du catalogue. Vérifier les populations et les clés avant de conclure. | Le notebook US-10 relève 800 échecs sur les dates, 8 426 sur le contrôle combinant âge et autres conditions, 120 sur le type de personne et 600 sur la durée. Les deux clés techniques testées n'ont aucun échec. Ces défauts demandent une analyse plutôt qu'un abaissement du seuil. | Data Owner — validation en attente | Réduire le seuil pour accepter les résultats actuels. Cela laisserait passer les anomalies sans en traiter la cause. |
| P-S2-02 | RQ-003 et RQ-005 | Garder le seuil proposé de 98 % et la sévérité avertissement. Examiner les possibilités de contact et les pays exclus du contrôle postal. | Le téléphone manque pour 5 995 des 49 978 souscripteurs testés : le taux atteint 88 %, soit 10 points sous le seuil. Le contrôle du CP atteint 98,48 %, avec 1 478 échecs sur 97 037 lignes. Preuve : US-10, cellules 9, 10 et 16. | Data Owner — validation en attente | Bloquer chaque dossier sans téléphone. L'intérêt de ce blocage dépend aussi des autres moyens de contact disponibles, qui n'ont pas été examinés ici. |
| P-S2-03 | RQ-002 et US-13 | Évaluer l'âge en années révolues au début du contrat, pour le souscripteur personne physique. Présenter séparément les cas dont l'âge ne peut pas être établi. | Les 8 426 échecs de la cellule 8 d'US-10 ne correspondent pas forcément à 8 426 mineurs : le test vérifie aussi le statut et la présence des dates. Le calcul comparatif et un cas réel divergent restent nécessaires. | Data Owner — validation en attente | Utiliser l'âge actuel. Une personne majeure aujourd'hui pouvait être mineure au début du contrat. |
| P-S2-04 | US-11 | Examiner d'abord les anomalies des règles proposées bloquantes, puis les problèmes de téléphone et d'adresse. Demander au Steward de préciser les causes et les actions. | US-10 annonce 17 419 occurrences d'échec. L'échantillon US-11 contient 7 occurrences RQ-002, 7 RQ-003 et 6 RQ-005. Il ne couvre donc pas toutes les familles d'erreurs et ses causes ne sont pas confirmées individuellement. | Data Owner — validation en attente | Présenter 17 419 clients touchés ou généraliser les proportions de l'échantillon. Une même ligne peut échouer à plusieurs règles et la sélection n'est pas représentative. |
| P-S2-05 | US-15 | Présenter une moyenne simple par dimension, accompagnée des résultats par règle et des limites de couverture. | Les moyennes recalculées sont de 100 % en unicité, 88 % en complétude, 97,33 % en validité et 99,20 % en cohérence. Leur calcul figure ci-dessous. L'enregistrement dans l'historique reste à démontrer. | Data Owner — validation en attente | Donner un seul score global. Il masquerait les règles en difficulté et ne montrerait pas les contrôles encore absents. |

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
