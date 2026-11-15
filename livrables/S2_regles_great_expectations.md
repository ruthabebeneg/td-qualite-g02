# S2 — Règles Great Expectations

G02 · lot `L-2026-10-01` · ingénieur qualité Maria Camila, Steward Ruth, Owner Iliana, rédaction Firdaouss.

## 1. Mesures par règle (US-10)

| Règle | Table Bronze | Testées | Échecs | Conformité | Sévérité / seuil |
|---|---|---|---|---|---|
| RQ-001 | crm_contrat | 100 000 | 800 | 99,20 % | BLOQUANTE / 100 % |
| RQ-002 | crm_contrat | 91 875 | 301 | 99,67 % | BLOQUANTE / 100 % |
| RQ-003 | crm_client | 49 978 | 5 995 | 88,00 % | AVERTISSEMENT / 98 % |
| RQ-005 | crm_client | 97 037 | 1 478 | 98,48 % | AVERTISSEMENT / 98 % |
| RQ-009 | crm_client | 100 000 | 200 | 99,80 % | BLOQUANTE / 100 % |
| RQ-010 | crm_contrat | 100 000 | 600 | 99,40 % | BLOQUANTE / 100 % |
| RQ-020 | crm_client | 100 000 | 0 | 100,00 % | BLOQUANTE / 100 % |
| RQ-020 | crm_contrat | 100 000 | 0 | 100,00 % | BLOQUANTE / 100 % |

Chaque expectation booléenne `expect_column_values_to_be_in_set` contient `meta.rule_id`. Paramètres : `DQ_SCHEMA`, `DQ_TABLE_CLIENT`, `DQ_TABLE_CONTRAT`, `DQ_TABLE_TYPE_CONTRAT`, `DQ_BATCH`. Les colonnes et la sémantique de la cible doivent rester compatibles ; renommer une table ne rend pas automatiquement sa structure compatible.

Les huit suites sont livrées sous `reports/ge/gx/expectations/`, classées par table et règle. Elles portent sur la colonne booléenne `conforme`, calculée par les prédicats métier du notebook : le contrat livré est **calcul métier + suite GE**, pas une suite autonome à appliquer directement à une table SQL brute. Elles sont sauvegardées, rechargées et validées dans `notebooks/S2_US10_regles_en_tests.ipynb`. Résultat agrégé : `reports/S2_execution.json`.

Pièges : RQ-003 distingue NULL, vide et blanc (5 995 absences sur 49 978 souscripteurs). RQ-005 S2 cible **97 037 pays exactement FR** (1 478 échecs) ; le contrôle S3/S4 après normalisation cible **98 037 pays FR** (1 493 échecs). Ces populations expliquent les deux mesures ; elles ne doivent pas être substituées l’une à l’autre. RQ-002 exclut personnes morales et références non évaluables de sa population métier, en les traitant séparément via l’intégrité.

## 2. Lignes en échec (US-11)

Export : `livrables/preuves/S2_US11_echecs_complets.csv` (**9 374 occurrences**, pas nécessairement autant de clients distincts). Échantillon déterministe : `livrables/preuves/S2_US11_echantillon_commente.csv`, **20 lignes**.

| Règle | Lignes de l’échantillon |
|---|---|
| RQ-001 | 4 |
| RQ-002 | 4 |
| RQ-003 | 3 |
| RQ-005 | 3 |
| RQ-009 | 3 |
| RQ-010 | 3 |

Chaque ligne contient famille, cause probable, action avec destinataire et `constat_factuel_automatique` individualisé à partir des valeurs (dates, âge, NULL/vide/blanc, CP, type ou durée). Les champs de confirmation humaine restent non renseignés : une cause probable n’est pas une cause confirmée. Notebook régénérateur : `notebooks/S2_US11_lignes_en_echec.ipynb` ; les exports utilisent directement le chemin remis.

## 3. Âge au début du contrat (US-13)

Population : 91 875 souscripteurs personnes physiques évaluables. **301** étaient mineurs au début du contrat ; **143** sont mineurs à la date de comparaison **15/11/2026** ; **158** classifications divergent. La comparaison se paramètre avec `DQ_COMPARISON_DATE` ; le jour d’exécution est utilisé par défaut et est affiché.

Cas réel `CT0000387` : naissance 28/09/1996, début 01/09/2014, **17 ans au début**, **30 ans au 15/11/2026**. Une majorité actuelle ne répare pas l’échec RQ-002 historique. Preuve : `notebooks/S2_g02.ipynb`, `reports/S2_analyse_reference.json`.

## 4. Référence par dimension (US-15)

| Dimension | Moyenne des couples règle/table | Règle la plus faible |
|---|---|---|
| Complétude | 88,00 % | RQ-003 |
| Cohérence | 99,20 % | RQ-001 |
| Validité | 99,34 % | RQ-005 |
| Unicité | 100,00 % | RQ-020 |

Même poids par couple règle/table ; seuls les huit identifiants réellement insérés par l’exécution US-10 liée dans `S2_execution.json` sont retenus. Un rapport d’un autre lot, schéma ou jeu de tables est refusé ; aucune combinaison silencieuse d’exécutions partielles. Cette moyenne n’est pas une proportion de clients sans défaut et ne compense jamais une règle bloquante. La validité corrigée est **99,34 %**, et non l’ancienne moyenne 97,33 %.

L’écriture utilise une connexion `WRITER` distincte de `reader`. La validation du 15/11 a écrit puis relu huit mesures dans `s5_test_audit_70dc04c654da`, ensuite supprimé. Cela vérifie réellement l’historisation tout en préservant `dq.dq_history` nominal lié au certificat GO. Les mesures historiques nominales restent présentes ; ne pas les réécrire après certification sans réémettre les preuves et l’approbation correspondantes.

## 5. Vérification et limites

- [x] Identifiant de règle dans chaque expectation et suites persistées/rechargées.
- [x] Export complet et échantillon de vingt lignes régénérés.
- [x] Calcul d’âge et cas divergent réexécutés.
- [x] Historisation et relecture testées dans un schéma isolé, nettoyé.
- [x] Trois notebooks S2 exécutés de bout en bout avec sorties.

Difficultés : permissions du compte lecteur et mauvais emplacement des exports corrigés ; temps historique non mesuré. Aucun point de reprise pédagogique restauré. Les erreurs présentes dans Bronze constituent le diagnostic attendu, pas un échec d’exécution de GE. Arbitrages : D-01/D-08 du journal ; aucune nouvelle décision métier créée par les corrections techniques.
