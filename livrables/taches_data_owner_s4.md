# Mes missions de Data Owner — S4

En S4, j'occupe le rôle de Data Owner. Je m'appuie sur les constats de S1 à S3 pour fixer les garde-fous métier et préparer mes décisions. Les décisions déjà inscrites pour S3 restent celles de Firdaouss; je les reprends comme références, sans les lui réattribuer. Mesures S4 : en attente des résultats reproductibles de l'Ingénieur qualité, avec validation métier du Data Steward.

## Mes décisions et consignes métier

### US-21 et US-22 — Silver et quarantaine

Objectif : Je fixe les garde-fous du nettoyage et de la quarantaine.

Ma consigne : On ne modifie pas le bronze. On doit retrouver chaque ligne en silver ou dans la quarantaine, avec sa règle et sa raison : pas de suppression silencieuse ni de valeur métier inventée. Je demande qu'on reprenne les conventions établies en S3 : 'assure_id = 0' signifie « pas d'assuré distinct » et devient 'NULL' en silver; un prospect qui a un contrat devient souscripteur en silver; on ne requalifie pas automatiquement un souscripteur sans contrat. On ne transforme pas arbitrairement une valeur inconnue en « Autre ».

### US-23 — Porte S

Objectif : J'examine les résultats et je décide si la porte S peut s'ouvrir.

Ma décision : On reprend les sévérités et seuils établis en S3 (D-07/D-08). Je ne donne pas le GO tant qu'une règle bloquante n'est pas conforme sur silver. On n'abaisse pas un seuil pour faire passer la porte; on explique chaque écart entre bronze et silver. Décision GO/non-GO : en attente des taux bronze/silver et de la preuve (Ingénieur qualité), ainsi que de l'interprétation des écarts (Data Steward).

### US-24 — Dédoublonnage

Objectif : Je fixe la politique de fusion et les seuils numériques après validation des mesures.

Ma décision : Je ne fixe pas de seuil numérique avant d'avoir les résultats sur les 200 paires étiquetées. On ne fusionne automatiquement que les paires au-dessus d'un seuil que j'aurai validé; on envoie les cas ambigus en revue. Seuils numériques : en attente des mesures de précision/rappel (Ingénieur qualité) et de la validation des paires ambiguës (Data Steward).

### US-25 — Golden record

Objectif : Je valide une règle de survie pour chacun des attributs.

Ma décision : Je ne privilégie pas systématiquement le CRM ou le CIF sans preuve de fiabilité. On retient une valeur non nulle et traçable; la provenance et la date de mise à jour doivent aider à départager les valeurs compatibles. Si les valeurs se contredisent et qu'on ne peut pas trancher avec les éléments disponibles, je demande une revue. Sources à retenir par attribut : en attente des valeurs et métadonnées (Ingénieur qualité) et des recommandations métier (Data Steward).

### US-27 — Gold et client actif

Objectif : Je vérifie les critères métier du gold et je décide si on peut le publier.

Ma décision : On reprend la définition CD-001 arrêtée en S3 : le client actif a un contrat en cours à la date de référence du lot et une dernière cotisation dans les trois mois. Je demande zéro orphelin et une seule vue 'v_client_actif' conforme à cette définition. Décision GO/non-GO de publication : en attente des comptages, contrôles d'intégrité et résultat de la vue (Ingénieur qualité), ainsi que de l'explication des exceptions métier (Data Steward).

### US-28 — Traçabilité

Objectif : Je vérifie que la traçabilité justifie les données publiées.

Ma consigne : Pour chacune des trois données, je demande la valeur gold, les identifiants de lignes silver et bronze, le lot, la table et la clé source, ainsi qu'une requête reproductible. On ne considère pas la publication justifiée si une trace est incomplète.

## Ce que j'attends de l'équipe avant de compléter les mesures

Résultats chiffrés S4 : en attente des mesures reproductibles de l'Ingénieur qualité; interprétation métier en attente du Data Steward.

### US-21 et US-22

En attente de : Chemins des scripts/notebooks; nombre de lignes modifiées par traitement; comptages bronze, silver et rejets par table; écart à 'silver + rejets = bronze'; rejets par règle et raison; preuve d'idempotence — Ingénieur qualité. Validation des raisons métier et des cas de correction/quarantaine — Data Steward.

### US-23

En attente de : Taux bronze et silver par règle, sévérité, écart et preuve reproductible — Ingénieur qualité. Interprétation des écarts et confirmation des populations métier — Data Steward.

### US-24

En attente de : Paramètres essayés, précision/rappel sur les 200 paires, volumes fusionnés, envoyés en revue et identités distinctes — Ingénieur qualité. Validation des étiquettes et examen des paires ambiguës — Data Steward. Je fixe les seuils après réception de ces éléments.

### US-25

En attente de : Valeurs candidates par attribut, provenance, dates de mise à jour et éléments disponibles sur leur qualité — Ingénieur qualité. Recommandations de source, exceptions métier et exemple d'échec de la règle — Data Steward. Je valide ensuite les règles de survie.

### US-27

En attente de : Comptages des tables gold et lignes écartées, règles responsables, orphelins, résultat de 'v_client_actif' comparé à CD-001 et effet de la quarantaine en aval — Ingénieur qualité. Explication des cas métier non conformes — Data Steward. Je prends ensuite la décision de GO/non-GO.

### US-28

En attente de : Traces des trois exemples avec valeur gold, identifiants de lignes silver/bronze, lot, source (table et clé) et requête reproductible — Ingénieur qualité. Vérification de la pertinence métier et de l'interprétation — Data Steward.

## Références S1-S3 dont je me sers

- En S1, on a relevé 2 156 personnes en doublon sous des identifiants différents. Cela justifie le dédoublonnage, mais ne suffit pas à fixer ses seuils.
- En S3, Firdaouss a consigné les décisions D-02 à D-04 sur la sentinelle et les corrections de statut, D-05/D-06 sur la date du lot et la définition CD-001, puis D-07/D-08 sur les sévérités et seuils. Je m'appuie sur ces décisions comme références pour S4.
- Le résultat S3 de 38 049 clients actifs correspond à la mesure du lot 'L-2026-10-01'; on ne le reprend pas comme mesure du gold S4.
