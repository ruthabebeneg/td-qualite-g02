# S4 — Mon travail de Data Owner

J'ai examiné le lot `L-2026-10-01` et la configuration `eed9d4937fbdd7ef476637ed8bde0f722421a5d7a18804f0a5d04b972e28ba61`. Mes décisions figurent dans le [manifeste Data Owner](../reports/S4_VALIDATION_DATA_OWNER.json) et le [journal des décisions](JOURNAL_DECISIONS.md).

## US-25 — Golden record

La preuve de traçabilité relie les quatre identifiants de la Société Meunier à la même identité `CLI-033864` :

| Source | Identifiant |
|---|---|
| CRM | `A-4471` |
| CRM | `H-9012` |
| CRM | `S-2208` |
| CIF | `K471226` |

J'ai accepté les seuils proposés : fusion automatique à partir de 90, revue de 75 à moins de 90, et pas de fusion sous 75. J'ai aussi accepté les garde-fous sur le type de personne, la date de naissance et les contradictions de pays ou de commune. Le Steward a classé 432 paires : 427 à maintenir séparées et 5 rapprochements à confirmer. Je ne valide pas de fusion sans preuve.

Pour la survie des attributs, j'ai accepté de garder seulement les contacts valides et de mettre `NULL` et le cas en revue s'il n'y en a pas. Pour les noms, la fréquence puis la complétude servent à départager les valeurs. La priorité CRM en cas d'égalité reste provisoire : elle ne prouve pas que la donnée est plus récente.

## US-27 — Gold cohérent

Pour le lot examiné, les tables Gold contiennent 121 073 clients, 139 556 correspondances d'identifiants, 96 159 contrats certifiés et 89 156 sinistres certifiés. Les contrôles ne trouvent pas de liens orphelins dans les populations vérifiées. Cela ne signifie pas que toutes les règles sont conformes.

La vue `v_client_actif` contient 36 165 clients actifs. La définition utilisée exige un contrat en cours au 01/10/2026 et une dernière cotisation depuis le 01/07/2026. Les trois lectures métier donnent le même résultat.

J'ai accepté de garder en `A_REVOIR` les anciens souscripteurs sans contrat certifié : leur absence de contrat dans l'extraction ne suffit pas à dire qu'ils sont prospects. J'ai également demandé une revue des identités en échec RQ-019, sans fusion automatique pour faire baisser le nombre d'anomalies.

## Décisions prises et résultat

| Proposition | Ma décision |
|---|---|
| P-S4-06 — Fusion des identités | Acceptée avec les seuils et garde-fous indiqués ci-dessus. |
| P-S4-07 — Survie des attributs | Acceptée avec les limites indiquées ci-dessus. |
| P-S4-08 — Adresses | Seuil de rapprochement accepté, mais la cible n'est pas atteinte : 7 997 adresses sur 100 000 restent non rapprochées. |
| P-S4-09 — Statuts historiques | Acceptée : conserver les cas incertains en `A_REVOIR`. |
| P-S4-10 — Acceptation de la configuration | Refusée. |
| P-S4-11 — Identités résiduelles | Revue acceptée. Pas de fusion automatique supplémentaire. |
| P-S4-12 — Résultat des contrôles Soda | Acceptée : distinguer le code technique du contrôle de la décision métier. |

Je refuse l'acceptation de cette configuration : RQ-019 reste en échec et RQ-016 atteint 96,80 %, sous le seuil de 98 %. Il n'y a donc pas de GO ni d'autorisation de publication pour ce lot.

## Suite de mes arbitrages

Pour l'instant, je n'ai pas demandé de travail supplémentaire à Iliana ou Firdaouss. J'ai décidé de ne pas fusionner les identités sans preuve, de garder les adresses non rapprochées en quarantaine et de laisser les statuts incertains en `A_REVOIR`.

Les anomalies sont toujours présentes dans la configuration que j'ai refusée. RQ-019 reste en échec et RQ-016 est sous le seuil attendu. Si la configuration change plus tard, les contrôles devront être relancés. Je pourrai alors regarder les nouveaux résultats avant de prendre une autre décision.

Le notebook vérifie déjà le fonctionnement des codes Soda PASS, WARN et FAIL. Il n'y a rien à ajouter sur ce point pour le moment.

Sources : [synthèse Steward](../reports/S4_steward_synthese.json), [couverture des règles](../reports/S4_couverture.json), [rapport d'acceptation](../reports/S4_acceptation.json) et [notebook S4](../notebooks/S4_g02.ipynb).

## Sources

- [Gabarit S4](S4_silver_gold.md) — contenu attendu pour la séance.
- [Manifeste Data Owner](../reports/S4_VALIDATION_DATA_OWNER.json) — décisions et configuration examinée.
- [Journal des décisions](JOURNAL_DECISIONS.md).
- [Synthèse d'acceptation](../reports/S4_acceptation.json) et [couverture des règles](../reports/S4_couverture.json).
- [Traçabilité Meunier](../reports/S4_traces_corrigees.json) et [synthèse Steward](../reports/S4_steward_synthese.json).
