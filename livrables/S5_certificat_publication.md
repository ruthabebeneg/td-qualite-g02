# S5 — Certificat, publication et gouvernance

G02 · lot `L-2026-10-01` · IQ Iliana, Steward Firdaouss, Owner Ruth, rédaction Maria Camila.

## 1. Historique et évolution (US-29/30)

Une mesure conserve règle, table, lot, couche, testées, échecs et date. Les préfixes S4/S4R19/S5 sont normalisés et la dernière mesure est sélectionnée par **id**, sans doublon en cas d’horodatage identique. Au sein d’une règle et couche, les taux ci-dessous sont pondérés par les lignes testées sur ses périmètres : les règles différentes ne sont pas confondues.

| Règle | Bronze | Silver | Gold |
|---|---|---|---|
| RQ-001 | 99,20 % | 100,00 % | 100,00 % |
| RQ-002 | 98,62 % | 98,60 % | 100,00 % |
| RQ-003 | 88,00 % | 88,05 % | 89,26 % |
| RQ-004 | 79,30 % | 99,28 % | 100,00 % |
| RQ-005 | 98,91 % | 100,00 % | 100,00 % |
| RQ-006 | 98,41 % | 99,49 % | 99,53 % |
| RQ-007 | 97,82 % | 100,00 % | 100,00 % |
| RQ-008 | 98,81 % | 98,81 % | 100,00 % |
| RQ-009 | 99,80 % | 100,00 % | 100,00 % |
| RQ-010 | 99,40 % | 100,00 % | 100,00 % |
| RQ-011 | 99,80 % | 99,80 % | 100,00 % |
| RQ-012 | 99,00 % | 98,59 % | 100,00 % |
| RQ-013 | 99,50 % | 99,05 % | 100,00 % |
| RQ-014 | 87,90 % | 100,00 % | 100,00 % |
| RQ-015 | 97,71 % | 100,00 % | 100,00 % |
| RQ-016 | 98,09 % | 97,65 % | 96,75 % |
| RQ-017 | 98,90 % | 98,30 % | 100,00 % |
| RQ-018 | 100,00 % | 100,00 % | 100,00 % |
| RQ-019 | 85,97 % | 85,99 % | 100,00 % |
| RQ-020 | 100,00 % | 100,00 % | 100,00 % |
| RQ-021 | 100,00 % | Non applicable / non mesurée ici | Non applicable / non mesurée ici |
| RQ-022 | 100,00 % | Non applicable / non mesurée ici | Non applicable / non mesurée ici |
| RQ-023 | Non applicable / non mesurée ici | 100,00 % | 100,00 % |
| RQ-024 | Non applicable / non mesurée ici | 100,00 % | Non applicable / non mesurée ici |

« Non applicable / non mesurée ici » signifie qu’aucun taux de ce couple ne figure dans l’export, et ne vaut jamais 100 %. RQ-021/022 concernent Bronze ; RQ-024 la conservation Silver ; RQ-025 la réconciliation CRM après publication. Les règles de porte G ne sont pas toutes des obligations sur Bronze.

Source : `reports/S5_export_steward.json`, avec populations détaillées dans sa matrice et sa couverture. Notebook réexécutable : `notebooks/S5_data_steward.ipynb`. Courbe : `reports/S5_US30_courbe.png`. Une variation de taux peut résulter d’un changement de population : la complétude du téléphone s’améliore (88,00 → 88,05 → 89,26 %) mais reste sous 98 % ; RQ-016 final reste à 96,75 % après exclusions de contrats et ne doit pas être masqué par une moyenne de dimension.

## 2. Certificat (US-31)

| Élément | Valeur |
|---|---|
| Certificat | `S5-d7c760617b538e9240c8541a4f7` |
| Lot | `L-2026-10-01` |
| Décision Python et SQL | GO |
| Couverture | 59 contrôles conformes sur 59 attendus, couvrant 18 règles sur B/S/G |
| Empreinte Gold | `a62b0b820e96225b76b20fa7aa0f5b3d4b84841a1c7770801e4e7fcb3ddd1667` |
| Approbation enregistrée | Ruth, Data Owner, 12/11/2026 |

Requête : `sql/S5_decision.sql`. Preuves : `reports/S5_certificat_final.json`, `reports/S5_VALIDATION_DATA_OWNER.json`, `reports/S5_preuves_finales.json`. Les avertissements sous seuil ne sont pas des règles bloquantes manquantes ; les 377 CLI exclus ne font pas partie du contenu autorisé.

Le NO_GO du lot initial est conservé dans les preuves antérieures ; les scénarios dégradés, absence de mesure et absence de décision Owner sont testés dans `pipelines/s5_tests.py`. **RQ-025 est contrôlée après publication**, séparément des 18 règles préalables au certificat.

## 3. Publication (US-32)

Exécuteur : `pipelines/s5_engineering.py`, notebook `notebooks/S5_g02.ipynb`.

| Scénario | Comportement | Preuve |
|---|---|---|
| Sans certificat | Refus, cible inchangée | `reports/S5_refus_nominal.json` |
| Certificat NO_GO | Refus, cible inchangée | même rapport |
| Gold altéré après certificat | Refus | `reports/S5_tests.json`, fixture isolée |
| GO et Gold intact | Chargement transactionnel, puis RQ-025 | `reports/S5_publication_reelle.json` |
| Lot déjà publié | Vérification du certificat, contenu, journal et intégrité, zéro écriture | `pipelines/audit_final.py`, nouvelle exécution notebook |

| Gold → CRM | Lignes Gold | Lignes cible | Écart | Empreintes identiques |
|---|---|---|---|---|
| client_unique → client | 120 673 | 120 673 | 0 | True |
| contrat_certifie → contrat | 95 822 | 95 822 | 0 | True |
| sinistre_certifie → sinistre | 88 824 | 88 824 | 0 | True |

La transaction englobe les trois tables, le journal et RQ-025. Une panne injectée entre tables produit un rollback intégral sur fixture préexistante ; les tests de rejeu ne créent aucun doublon de données. Les modules liés à la politique du certificat historique restent inchangés. Les nouvelles traces de rejeu sont écrites sous `reports/executions/`, pas à la place des preuves historiques.

## 4. Catalogue et décisions (US-34)

`catalogue/gold_client_unique.md` et `catalogue/catalogue.yml` : Owner Ruth, Steward Firdaouss, définition CD-001, règles RQ et lineage CRM/CIF → Bronze → Silver → xref → Gold. Le statut dépend des contrats certifiés ; 1 569 dossiers A_REVOIR ne deviennent pas automatiquement prospects. Journal : D-21 à D-27 pour S5, dont l’approbation finale D-27. Les décisions préalables restent datées comme historiques.

## 5. Fin et réserves

- [x] NO_GO et refus démontrés ; GO nominal approuvé et publié.
- [x] Comptages et empreintes Gold/CRM identiques sur trois tables.
- [x] Rejeu en lecture seule, chemin portable et contrôle du contenu.
- [x] Rôles, catalogue et lineage renseignés.

Réserves métier maintenues : 377 CLI hors publication, 23 consolidations sans confirmation humaine, 1 569 statuts à revoir et 5 190 téléphones absents. Revue Steward avant réintégration ; échéance indiquée dans le dossier du 15/11 : 20/12/2026. Ce sont des conditions de suivi explicites, pas une nouvelle approbation créée par l’audit. Temps historique non mesuré ; aucune restauration pédagogique. US-33 orchestration demeure facultative et non retenue.

## Complément de preuve US-30 et ligne SQL (15/11/2026)

La ligne SQL complète, comparée au SELECT réel sans écriture, est jointe dans `preuves/S5_certificat_ligne_sql.json` : GO, Ruth, 59 bloquantes testées et 59 conformes. Aucune réémission du certificat.

Démonstration pédagogique **synthétique**, distincte des courbes et de l’historique certifiés : `python3 scripts/demo_us30.py --output reports/executions/conformite_prof_20261115/us30_demo.json --svg reports/executions/conformite_prof_20261115/us30_demo.svg`. Le même prédicat SQL RQ-001 est exécuté deux fois sur quatre contrats fictifs SQLite en mémoire : 2 échecs/4 puis 2/4 (50 % → 50 %, plateau). Deux dates de la fixture sont corrigées puis remesurées : 0/4 (100 %, progression). Ce résultat réellement exécuté ne prétend pas documenter une exécution historique du lot nominal. Aucun effet sur les mesures ou le certificat nominaux.

![US30 : démonstration synthétique plateau puis progression](../reports/executions/conformite_prof_20261115/us30_demo.svg)
