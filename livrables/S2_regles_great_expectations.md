# S2 · Great Expectations : des règles en tests automatisés

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-2`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Règles en tests (US-10)

Une ligne par règle. L'expectation porte son `rule_id` ; la base et la table visées sont des paramètres.

| Règle | Table bronze | Expectation (type) | Lignes testées | Lignes en échec | Taux de réussite | Sévérité retenue (bloquante / avertissement) |
|---|---|---|---|---|---|---|
| RQ-001 | … | … | … | … | … | … |
| RQ-002 | … | … | … | … | … | … |
| RQ-003 | … | … | … | … | … | … |
| RQ-005 | … | … | … | … | … | … |
| RQ-009 | … | … | … | … | … | … |
| RQ-010 | … | … | … | … | … | … |
| RQ-020 | … | … | … | … | … | … |

Pièges rencontrés et traitement (nul, vide, blanc ; adresses étrangères ; comparaisons exactes) :

| Règle | Piège | Chiffre avant correction | Chiffre après correction | Preuve |
|---|---|---|---|---|
| … | … | … | … | … |
| … | … | … | … | … |

Suites de validation (chemins) : [À COMPLÉTER]

## 2. Lignes en échec (US-11)

Export complet : [À COMPLÉTER chemin]. Échantillon commenté de 20 lignes : [À COMPLÉTER chemin]

| Règle | Famille d'erreur observée | Nombre de lignes de l'échantillon | Cause probable | Action proposée (à qui ?) |
|---|---|---|---|---|
| … | … | … | … | … |
| … | … | … | … | … |
| … | … | … | … | … |

## 3. Âge à la date de début du contrat (US-13, RQ-002)

| Date de référence | Définition de l'âge | Lignes en échec | Preuve |
|---|---|---|---|
| Date de début du contrat | … | … | … |
| Date du jour | … | … | … |

Un cas où « à la date du jour » donne un autre résultat, et pourquoi : [À COMPLÉTER]

## 4. Mesure de référence sur bronze (US-15)

Écrite dans `dq.dq_history`, couche BRONZE, lot : [À COMPLÉTER]

| Dimension | Règles | Taux moyen | Règle la plus faible | Constat |
|---|---|---|---|---|
| Unicité | … | … | … | … |
| Complétude | … | … | … | … |
| Validité | … | … | … | … |
| Cohérence | … | … | … | … |

Phrase de synthèse (« Voici la qualité de ce qui nous est livré : … ») : [À COMPLÉTER]

## 5. Critères de fin

- [ ] Chaque expectation porte l'identifiant de sa règle.
- [ ] La même suite se relance sur une autre base ou table sans modification de code.
- [ ] La mesure de référence est dans `dq.dq_history` avec le lot, la couche, les lignes testées et les échecs.
- [ ] Les règles sont exécutables d'un seul geste (script ou notebook relançable de bout en bout).

## 6. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]
