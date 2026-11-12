# S5 — Publication réelle et preuves finales du Data engineer

Le 12/11/2026, le code de `main` (`e26be87`) a été intégré par avance rapide. Les décisions D-21 à D-27 et l'approbation signée de Ruth dans `reports/S5_VALIDATION_DATA_OWNER.json` ont permis de réémettre le certificat **GO** `S5-d7c760617b538e9240c8541a4f7` : 59 périmètres bloquants attendus, testés et conformes, aucun motif de refus.

La publication `d2813a2f27c741dcadc379c43c892c90` du lot `L-2026-10-01` a été exécutée entre 2026-11-12T15:53:40.583201+00:00 et 2026-11-12T15:57:29.423948+00:00 (UTC, contrôles complets inclus). Les trois tables `crm_cible` étaient vides avant chargement. Le chargement, les contrôles avant commit, les trois mesures RQ-025 et le journal de publication sont transactionnels.

| Table cible | Lignes gold | Lignes cible après commit | Écart | SHA256 identique |
|---|---:|---:|---:|---|
| client | 120673 | 120673 | 0 | Oui |
| contrat | 95822 | 95822 | 0 | Oui |
| sinistre | 88824 | 88824 | 0 | Oui |

Une nouvelle connexion confirme les comptages et SHA256 après commit. Aucun orphelin souscripteur, assuré ou contrat de sinistre. Les empreintes intégrales des 24 tables sources/bronze/silver/gold sont identiques avant et après. Les codes postaux, NULL, chaînes vides, espaces et décimaux sont inclus dans les empreintes typées.

Preuves à transmettre :

- [Certificat GO final](../reports/S5_certificat_final.json), également courant dans `reports/S5_certificat.json`.
- [Publication transactionnelle réelle](../reports/S5_publication_reelle.json), avec état cible avant chargement et réconciliation avant commit.
- [Contrôle indépendant après commit, historique RQ-025, journal SQL et immutabilité](../reports/S5_preuves_finales.json).
- [Notebook S5](../notebooks/S5_g02.ipynb), dernière cellule exécutée et sorties agrégées ; les cellules antérieures conservent les preuves NO_GO historiques.
- [Approbation humaine](../reports/S5_VALIDATION_DATA_OWNER.json) et [décisions](../livrables/JOURNAL_DECISIONS.md).

Reprise : ne pas exécuter tout le notebook pour republier, car les cellules historiques recalculent l'historique approuvé. La dernière cellule contient l'appel `certify` avec l'approbation et l'attestation existantes, puis `prepare_target` et `publish`. Adapter `ROOT` au répertoire contenant `pipelines/`, `sql/` et `reports/`. Le répertoire temporaire utilisé lors de cette exécution est `/tmp/s5-final` dans `dq_jupyter`, alimenté depuis ce dépôt ; les fichiers utiles ont été rapatriés. Le rejeu remplace le même lot transactionnellement et ajoute une trace de publication, sans ajout de doublons dans la cible.

Les 377 CLI incertains et leurs dépendances exclus ne sont pas déclarés réparés ou migrés ; les réserves D-24/D-26 et l'avertissement RQ-016 restent applicables. Les courbes, le catalogue, l'assemblage PPTX et la décision de restitution restent aux rôles concernés. Les sections techniques du livrable S5 et US-29/31/32 sont mises à jour ; S5 globale n'est pas déclarée complète.

Le contrôle documentaire global passe, mais ne valide ni le sens des réponses ni le PPTX. Les tests de panne/tout-ou-rien et de gold altéré sont les preuves synthétiques antérieures conservées dans `reports/S5_tests.json` ; aucune panne n'a été provoquée dans le lot réel. Difficultés observées : intégration Docker WSL indisponible et montages vides ; accès par Docker Desktop et transfert temporaire. Temps perdu humain non mesuré. Aucun commit, tag ou push effectué dans cette intervention.
