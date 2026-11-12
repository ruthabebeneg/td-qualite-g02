# Fiche de catalogue — `gold.client_unique`

| Élément | Valeur |
|---|---|
| Couche | GOLD (porte G) |
| Description | Une ligne par personne consolidée CRM + CIF (golden record), identifiée par un CLI |
| Clé | `cli_id` (format `CLI-NNNNNN`) |
| Propriétaire (Data Owner) | Ruth — décide des seuils, de la règle de survie et de la publication |
| Steward (Data Steward) | Firdaouss — tient les définitions, les règles rattachées, instruit les écarts |
| Sensibilité | Données personnelles (RGPD) : nom, date de naissance, téléphone, courriel |
| Volume (lot L-2026-10-01) | 120 673 CLI pour 139 160 identifiants sources retenus ; 377 CLI (396 identifiants) en quarantaine G après la résolution RQ-019 |

## Définitions rattachées

- **Client actif (fiche CD-001)** : un CLI qui souscrit au moins un contrat certifié en cours à la date de référence du lot (01/10/2026 pour `L-2026-10-01`) **et** dont la dernière cotisation date de moins de 3 mois. Décisions D-05 et D-06. Publié par la seule vue `gold.v_client_actif` (36 041 clients actifs), lue à l'identique par les trois directions (RQ-018).
- **Statut client** : calculé à partir des contrats certifiés (D-04) : `ACTIF`, `INACTIF`, `ASSURE`, `PROSPECT`. `A_REVOIR` : ancien souscripteur sans contrat certifié, à confirmer par le métier (D-17, 1 569 cas dans le gold certifié).
- **Règle de survie** : valeur valide, puis la plus fréquente, puis la plus complète pour le nom ; sans valeur valide, `NULL` et mise en revue (D-15).

## Règles RQ rattachées

| Règle | Objet | Sévérité |
|---|---|---|
| RQ-003, RQ-004, RQ-005, RQ-006, RQ-008 | téléphone, code postal, couple CP/commune, courriel | Avertissement |
| RQ-007, RQ-009 | pays ISO, type de personne | Bloquante |
| RQ-015, RQ-016 | cohérence du statut avec les contrats | Bloquante / Avertissement |
| RQ-018 | client actif identique pour les trois directions | Bloquante |
| RQ-019 | une personne = un seul CLI | Bloquante |
| RQ-020, RQ-023 | clé unique, traçabilité vers bronze | Bloquante |
| RQ-025 | réconciliation gold → CRM après publication | Bloquante |

## Lineage jusqu'aux sources

```
crm.client   ─► bronze.crm_client  ─┐                         (RQ-021, RQ-022 : source → bronze)
cif.clients  ─► bronze.cif_clients ─┴─► silver.client ─► gold.xref_identifiants ─► gold.client_unique
                                         ▲  (RQ-023, RQ-024 ; silver.ref_pays, silver.ref_postal)
crm.contrat  ─► bronze.crm_contrat ─► silver.contrat ─► gold.contrat_certifie ─► statut_client, gold.v_client_actif
```

Preuve que chaque saut est retrouvé : `notebooks/S5_data_steward.ipynb`, section 5. Requête de trace ligne à ligne : `pipelines/S4_US28_tracabilite.sql`.
