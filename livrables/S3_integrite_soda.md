# S3 — Intégrité et contrôles Soda

G02 · lot `L-2026-10-01` · ingénieure qualité Ruth, Data Steward Maria Camila, Data Owner Firdaouss, rédaction Iliana.

## 1. Configuration et checks (US-12)

La configuration est dans `soda/configuration.yml`. Les fichiers `soda/checks/bronze_client_checks.yml`, `soda/checks/bronze_contrat_checks.yml` et `soda/checks/bronze_sinistre_checks.yml` contrôlent Bronze avec un filtre de lot sur les tables et leurs relations. Les fichiers sans préfixe Bronze servent au diagnostic des sources ; `client_unique_checks.yml` contrôle Gold. Les mesures complètes Silver et Gold sont présentées dans S4 et S5.

Commandes depuis le conteneur :

```bash
python soda/run_scan.py -d bronze -c soda/configuration.yml -v BATCH_ID=L-2026-10-01 -v REFERENCE_DATE=2026-10-01 --results reports/executions/conformite_prof_20261115/soda_bronze.json soda/checks/bronze_client_checks.yml soda/checks/bronze_contrat_checks.yml soda/checks/bronze_sinistre_checks.yml
python soda/run_scan.py -d crm -c soda/configuration.yml -v REFERENCE_DATE=2026-10-01 soda/checks/client_checks.yml soda/checks/contrat_checks.yml soda/checks/sinistre_checks.yml
python soda/run_scan.py -d gold -c soda/configuration.yml soda/checks/client_unique_checks.yml
```

Le scan Bronze du lot donne **16 PASS / 1 WARN / 10 FAIL sur 27 contrôles**, sans erreur technique, avec un code de sortie 2. Il comprend trois contrôles de présence du lot. Le diagnostic CRM donne **13 PASS / 1 WARN / 10 FAIL sur 24 contrôles**. Ces résultats décrivent les anomalies des données brutes ; ils ne constituent pas une décision de publication Gold. L’exécuteur distingue les échecs bloquants, les avertissements et les erreurs techniques. Preuve Bronze : `reports/executions/conformite_prof_20261115/soda_bronze.json`.

Les contrôles RQ-001/007/009 prennent en compte les valeurs NULL. RQ-014 BAN échoue dès un défaut sur sa population, conformément à la règle bloquante à 100 %. L’unicité de `cli_id` porte RQ-020 ; RQ-019 recherche une même signature métier sur plusieurs CLI distincts.

## 2. Bilan des relations (US-16/17)

| Relation source | Testées | Orphelins | Interprétation |
|---|---:|---:|---|
| contrat.souscripteur_id → client | 100 000 | 1 000 | Anomalies de référence |
| contrat.assure_id → client, avant convention | 100 000 | 40 300 | 40 000 sentinelles et 300 vraies anomalies |
| contrat.assure_id → client, après NULLIF | 100 000 | 300 | 0 signifie absence d’assuré distinct |
| contrat.code_type → type_contrat | 100 000 | 200 | Produit T13 à instruire, pas de création arbitraire |
| sinistre.contrat_id → contrat | 100 000 | 0 | Aucun orphelin source |

Preuve exécutée : `notebooks/S3_g02.ipynb`, sorties du bilan. Convention D-02 : conserver 0 dans Bronze, remplacer par NULL dans Silver. Les 40 000 sentinelles expliquent 99,26 % des faux orphelins initiaux.

## 3. Statuts et garantie (US-18/19)

| Règle | Population source | Échecs | Résultat |
|---|---:|---:|---|
| RQ-015 prospect avec contrat | 20 978 prospects normalisés | 487 | Requalifier en Silver, D-03 |
| RQ-016 souscripteur sans contrat | 49 978 | 990 | 98,02 %, avertissement ; pas de requalification arbitraire, D-04 |
| RQ-017 période du contrat référencé | 100 000 sinistres | 1 200 | 480 avant début, 720 après fin ; traitement des renouvellements précisé en D-12 pour l’aval |

Les libellés exacts et les libellés normalisés donnent des populations différentes : 479 prospects avec contrat avant normalisation, 487 après ; 955 souscripteurs sans contrat avant normalisation, 990 après. Le tableau utilise les populations normalisées.

## 4. Définition commune (US-14)

Requête : `queries/S3_US14_client_actif.sql`. Référence 01/10/2026 ; contrat en cours et dernière cotisation depuis 01/07/2026 (D-05/D-06). Les trois directions obtiennent **38 049** sur Bronze filtré par `_batch_id` (confirmé par SELECT nominal) ; écart RQ-018 **0**. Le chiffre Gold final **36 041 CLI actifs** porte sur le périmètre certifié après exclusions et consolidation, donc ne remplace pas le diagnostic source.

## 5. Bilan et périmètres de mesure

- [x] Convention sentinelle et statuts attribués au Data Owner.
- [x] Relations et définition commune documentées avec chiffres et requête.
- [x] Checks bloquants, avertissements et cas NULL vérifiés ; contrôle métier d’identité distinct du contrôle de clé.

Preuves : `notebooks/S3_g02.ipynb`, les rapports Soda et `reports/executions/conformite_prof_20261115/verification_db.json`. Le notebook présente quatre exemples de cinq lignes. Les tests multi-lots vérifient que les relations ne sont pas validées à partir de données d’un autre lot. Les temps de traitement ne sont pas disponibles. L’extension US-20 n’est pas terminée.

RQ-005 : CRM et Bronze lot mesurent FR exact (1 456 échecs sur 95 437, conformité 98,47 %). GE S2 normalise trim+upper et FR/FRANCE (1 478 échecs sur 97 037, conformité 98,48 %). Diagnostic S4 normalise aussi F/Frnace (1 493 échecs sur 98 037, conformité 98,48 %). Aucune identité des populations déduite des taux arrondis.

Portée de RQ-018 : trois réexécutions de la même définition CD-001 démontrent la définition commune. Ce calcul n’est pas une comparaison indépendante de résultats fournis par trois directions.
