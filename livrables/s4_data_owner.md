# S4 — Décisions du Data Owner

Groupe G02 · lot `L-2026-10-01` · Data Owner : Ruth.

Ce document présente les choix sur le rapprochement des identités, la survie des valeurs et le périmètre Gold. Le [journal des décisions](JOURNAL_DECISIONS.md) conserve les références D-14 à D-27.

## 1. Rapprochement et fiche de référence (US-24/25)

La Société Meunier est reliée à l’identité `CLI-033864` à partir de quatre fiches :

| Source | Identifiant |
|---|---|
| CRM | `A-4471` |
| CRM | `H-9012` |
| CRM | `S-2208` |
| CIF | `K471226` |

Le Data Owner a retenu une fusion automatique à partir de 90, une revue de 75 inclus à moins de 90 et un maintien séparé sous 75. La nature de personne doit être connue et identique ; les personnes physiques doivent avoir la même naissance. Les contradictions géographiques et les incompatibilités entre paires empêchent une fusion automatique.

Sur les 200 paires évaluées, la précision est de 100 % et le rappel de 95 %. Ce résultat ne garantit pas toutes les identités. Parmi les 432 paires examinées par le Steward, 427 sont recommandées comme distinctes et cinq rapprochements restent à confirmer.

## 2. Choix des valeurs (US-25)

Pour les contacts, seuls les candidats valides sont retenus. Sans candidat valide, la valeur reste `NULL` et le dossier part en revue. Pour le nom et le prénom, la fréquence puis la complétude départagent les valeurs. L’adresse, le code postal, la commune et le pays restent un ensemble cohérent.

La priorité CRM dans certains cas d’égalité est provisoire : les sources ne donnent pas un horodatage fiable permettant de choisir systématiquement la valeur la plus récente.

## 3. Adresses et statuts (US-26/27)

Le rapprochement BAN utilise un seuil de 90 avec concordance du numéro, du code postal et de la commune. En cas d’égalité, aucun candidat n’est choisi automatiquement. Les 7 997 adresses non rapprochées sur 100 000 restent isolées ; la cible de 2 % n’est pas atteinte.

Les anciens souscripteurs sans contrat certifié restent `A_REVOIR`. L’absence de contrat dans l’extraction ne suffit pas à les classer comme prospects.

## 4. Refus de la configuration S4 du 08/11/2026

Le Data Owner a refusé la configuration `eed9d4937fbdd7ef476637ed8bde0f722421a5d7a18804f0a5d04b972e28ba61` : RQ-019 échouait sur quatre populations Gold. RQ-016 atteignait 96,80 %, sous son seuil d’avertissement de 98 %. Le refus de publication reposait sur les échecs bloquants RQ-019 ; l’avertissement RQ-016 restait à suivre.

Cette configuration contenait 121 073 identités, 139 556 correspondances, 96 159 contrats et 89 156 sinistres ; la vue des clients actifs comptait 36 165 CLI. Ces volumes décrivent le périmètre examiné à cette date, pas la publication finale.

Preuve : [validation S4](../reports/S4_VALIDATION_DATA_OWNER.json), décision D-18.

## 5. Périmètre accepté le 12/11/2026

La résolution RQ-019 a consolidé 23 cas et isolé 377 CLI, soit 396 identifiants sources, ainsi que 337 contrats et 332 sinistres associés. Le Data Owner a accepté la configuration `59628e7756fc09172c20d08a8cb00aa57defdc1f96f04b9e7aae5780b8156d33` dans D-21.

| Population finale Gold | Volume |
|---|---:|
| Clients uniques | 120 673 |
| Correspondances sources | 139 160 |
| Contrats certifiés | 95 822 |
| Sinistres certifiés | 88 824 |
| Clients actifs selon CD-001 | 36 041 |

Le certificat `S5-d7c760617b538e9240c8541a4f7` est GO, avec 59 contrôles bloquants conformes sur 59 attendus. Ruth a approuvé le contenu et autorisé sa publication dans D-23/D-27. Les volumes et empreintes Gold/CRM concordent après chargement.

Les 377 CLI restent exclus jusqu’à preuve d’identité. Les 23 consolidations publiées attendent une confirmation humaine. Les 1 569 statuts `A_REVOIR` et les téléphones absents restent suivis ; le GO ne lève pas ces réserves.

## 6. Preuves

- [Résolution des identités](../reports/S4_RQ019_resolution.json).
- [Traçabilité de Meunier et des deux transformations](../reports/S4_traces_corrigees.json).
- [Approbation du Data Owner](../reports/S5_VALIDATION_DATA_OWNER.json).
- [Certificat](../reports/S5_certificat_final.json) et [réconciliation finale](../reports/S5_preuves_finales.json).
- [Résultats S4](S4_silver_gold.md), [résultats S5](S5_certificat_publication.md) et [dossier de décision](DOSSIER_GO_NOGO.md).
