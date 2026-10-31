-- RQ-018 — client actif selon la decision Data Owner D-05/D-06.
-- Adapter cette date a la date du lot, puis executer le SELECT pour chaque direction.
SET @date_reference = DATE('2026-10-01');

SELECT COUNT(DISTINCT c.souscripteur_id) AS clients_actifs
FROM crm.contrat AS c
WHERE c.souscripteur_id IS NOT NULL
  AND c.date_debut <= @date_reference
  AND c.date_fin >= @date_reference
  AND c.date_derniere_cotisation >= DATE_SUB(@date_reference, INTERVAL 3 MONTH);
