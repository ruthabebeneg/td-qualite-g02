-- US-14 / CD-001 ; Bronze immuable, un lot et une date explicites.
-- Trois directions appliquent cette même définition (D-05/D-06).
SET @batch_id = 'L-2026-10-01';
SET @date_reference = '2026-10-01';

SELECT COUNT(DISTINCT c.souscripteur_id) AS clients_actifs
FROM bronze.crm_contrat c
WHERE c._batch_id = @batch_id
  AND c.souscripteur_id IS NOT NULL
  AND STR_TO_DATE(c.date_debut, '%Y-%m-%d') <= STR_TO_DATE(@date_reference, '%Y-%m-%d')
  AND STR_TO_DATE(c.date_fin, '%Y-%m-%d') >= STR_TO_DATE(@date_reference, '%Y-%m-%d')
  AND c.date_derniere_cotisation IS NOT NULL
  AND STR_TO_DATE(c.date_derniere_cotisation, '%Y-%m-%d') >= DATE_SUB(
      STR_TO_DATE(@date_reference, '%Y-%m-%d'), INTERVAL 3 MONTH
  );
