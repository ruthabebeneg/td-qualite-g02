# S5 · Certifier, publier vers le CRM, gouverner

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-5`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Historique des mesures (US-29, US-30)

Une ligne par règle mesurée ; laissez vide la couche où la règle ne s'applique pas, et dites pourquoi.

| Règle | Dimension | Taux bronze | Taux silver | Taux gold | Évolution (monte, stable, descend) | Explication |
|---|---|---|---|---|---|---|
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |

Courbes (chemin des images) : [À COMPLÉTER]

Toute règle qui descend d'une couche à l'autre : cause (filtre mal posé, conversion, effet de la quarantaine) et preuve : [À COMPLÉTER]

## 2. Certificat de qualité (US-31)

Exécution finale du Data engineer : 12/11/2026, code de `main` au commit `e26be87`. Approbation humaine : `reports/S5_VALIDATION_DATA_OWNER.json`, décisions D-21 à D-27. Les métadonnées de rédaction et les rubriques des autres rôles restent à compléter.

| Élément | Valeur |
|---|---|
| Numéro du certificat | `S5-d7c760617b538e9240c8541a4f7` |
| Lot | `L-2026-10-01` |
| Décision | **GO** |
| Périmètres bloquants attendus / testés / conformes | 59 / 59 / 59 |
| Avertissements | Voir `avertissements` dans `reports/S5_certificat_final.json` ; RQ-016 gold : 1 569 échecs / 48 322, conformité 96,753 % face à 98 % |
| Empreinte du gold | `a62b0b820e96225b76b20fa7aa0f5b3d4b84841a1c7770801e4e7fcb3ddd1667` |
| Signataire | Ruth, Data Owner, décision du 12/11/2026 dans le fichier d'approbation signé |

Requête de décision : `sql/S5_decision.sql`, appelée par `pipelines/s5_engineering.py::certify`. Preuve réelle : `reports/S5_certificat_final.json`. Le certificat NO_GO antérieur reste dans `reports/S5_verification_complete.json` et en base.

Épreuve du NO_GO : contrat synthétique volontairement dégradé, voir `reports/S5_tests.json` ; cette épreuve reste explicitement isolée du lot réel. Le nominal réel est maintenant GO. Les 59 périmètres bloquants attendus avant publication sont couverts ; RQ-025, porte C, est contrôlée au chargement puis après commit. Ce GO ne déclare pas les dossiers exclus réparés : 377 CLI, 396 sources clients, 337 contrats et 332 sinistres supplémentaires restent exclus selon D-21/D-24/D-26.

## 3. Publication vers le CRM (US-32)

Traitement : `pipelines/s5_engineering.py::publish`, appelé dans la dernière cellule exécutée de `notebooks/S5_g02.ipynb`. Publication réelle : `reports/S5_publication_reelle.json`. Contrôle après commit : `reports/S5_preuves_finales.json`.

| Scénario | Message obtenu | Chargement effectué ? | Preuve |
|---|---|---|---|
| Sans certificat | `CERTIFICAT_ABSENT` | Non | `reports/S5_refus_nominal.json`, épreuve réelle antérieure |
| Certificat NO_GO | `CERTIFICAT_NO_GO` | Non | `reports/S5_refus_nominal.json`, épreuve réelle antérieure |
| Gold modifié après émission du certificat | `EMPREINTE_GOLD_DIFFERENTE` | Non | `reports/S5_tests.json`, scénario synthétique isolé |
| Certificat GO et gold intact | `CHARGEE` | Oui, lot réel | `reports/S5_publication_reelle.json` |

Réconciliation RQ-025, gold contre CRM cible ; SHA256 sur toutes les colonnes, types et lignes du lot :

| Table | Lignes gold | Lignes CRM cible | Somme de contrôle gold | Somme de contrôle CRM cible | Écart |
|---|---:|---:|---|---|---:|
| client | 120673 | 120673 | `b1e83124dafb52a5da8906b5954d46d8b082ddd87d69e030baf2a439d2ca750a` | `b1e83124dafb52a5da8906b5954d46d8b082ddd87d69e030baf2a439d2ca750a` | 0 |
| contrat | 95822 | 95822 | `7d784b055187f3ec20eb3d94785f9deeece8d715f79a5d19e9aafc62b3001c12` | `7d784b055187f3ec20eb3d94785f9deeece8d715f79a5d19e9aafc62b3001c12` | 0 |
| sinistre | 88824 | 88824 | `fde4c59ef4686ae5ebd82e040f0985fcb97888a74cf3688c395d3a4bca813675` | `fde4c59ef4686ae5ebd82e040f0985fcb97888a74cf3688c395d3a4bca813675` | 0 |

Le chargement utilise une transaction InnoDB unique : suppression du lot, insertions des trois tables, réconciliation et journalisation avant commit ; tout écart provoque un rollback. Les injections de panne après chargement et pendant la journalisation sont démontrées sur fixtures dans `reports/S5_tests.json`. Aucun défaut n'est injecté dans le lot réel. La preuve finale relit les trois tables avec une nouvelle connexion après commit et vérifie aussi l'intégrité cible et l'immutabilité des sources/bronze/silver/gold.

## 3 bis. Gouvernance (US-34)

Fiche de catalogue de `gold.client_unique` (chemin) : [À COMPLÉTER]

| Élément | Valeur |
|---|---|
| Propriétaire (Data Owner) | … |
| Steward (Data Steward) | … |
| Définition de « client actif » rattachée à la fiche | … |
| Règles RQ rattachées à la table | … |

Lineage de `gold.client_unique` jusqu'aux sources (liste ou schéma) : [À COMPLÉTER]

## 4. Décisions de la séance

Reportez dans `JOURNAL_DECISIONS.md` chaque seuil, sévérité ou règle de survie arrêté, avec son rôle. Nombre de décisions ajoutées en S5 : [À COMPLÉTER]

## 5. Critères de fin

- [x] Un lot volontairement dégradé produit un NO_GO, le lot nominal un GO.
- [x] La publication refuse sans certificat, avec une décision NO_GO, et quand le gold a changé (épreuves réelles et synthétiques distinguées ci-dessus).
- [x] Après un chargement réussi, comptage et somme de contrôle sont égaux entre gold et CRM cible.
- [ ] Chaque décision de seuil ou de sévérité est attribuée à un rôle.

## 6. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]
