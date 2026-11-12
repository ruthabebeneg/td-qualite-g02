-- Exécutée par s5_engineering.certify sur MariaDB, dans le même snapshot.
-- :scopes = JSON de périmètres explicites ; aucune absence ne vaut conformité.
WITH attendus AS (
 SELECT j.* FROM JSON_TABLE(:scopes, '$[*]' COLUMNS (
  rule_id VARCHAR(10) PATH '$.rule_id', couche VARCHAR(10) PATH '$.couche',
  table_logique VARCHAR(60) PATH '$.table_logique', seuil DECIMAL(5,2) PATH '$.seuil_min'
 )) j
), historique AS (
 SELECT h.*, ROW_NUMBER() OVER(PARTITION BY couche,rule_id,
  CASE WHEN LEFT(table_cible,6)='S4R19_' THEN SUBSTRING(table_cible,7)
   WHEN LEFT(table_cible,3) IN ('S4_','S5_') THEN SUBSTRING(table_cible,4) ELSE table_cible END
  ORDER BY id DESC) rn,
  CASE WHEN LEFT(table_cible,6)='S4R19_' THEN SUBSTRING(table_cible,7)
   WHEN LEFT(table_cible,3) IN ('S4_','S5_') THEN SUBSTRING(table_cible,4) ELSE table_cible END table_logique
 FROM {dq_history} h WHERE batch_id=:batch
), couverture AS (
 SELECT a.*,h.id,h.nb_testees,h.nb_echecs,
  COALESCE(h.nb_testees>0 AND h.nb_echecs BETWEEN 0 AND h.nb_testees
   AND 100*(h.nb_testees-h.nb_echecs)>=a.seuil*h.nb_testees,0) conforme
 FROM attendus a LEFT JOIN historique h ON h.rn=1 AND h.rule_id=a.rule_id
  AND h.couche=a.couche AND h.table_logique=a.table_logique
)
SELECT COUNT(*) nb_attendues,
 COALESCE(SUM(id IS NOT NULL AND nb_testees>0),0) nb_testees,
 COALESCE(SUM(conforme),0) nb_conformes,
 CASE WHEN COUNT(*)>0 AND COALESCE(SUM(conforme),0)=COUNT(*)
  AND :owner_valide=1 AND :historique_valide=1 AND :gold_non_vide=1
  AND :catalogue_complet=1 AND :mesures_attestees=1 AND :integrite_gold=1 THEN 'GO' ELSE 'NO_GO' END decision
FROM couverture
