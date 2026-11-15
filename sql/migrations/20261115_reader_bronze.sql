-- Compatibilité des volumes créés avant l'ajout du droit dans initdb/00_medallion.sql.
-- Lecture seule : aucune donnée source, Bronze, Silver ou Gold n'est modifiée.
GRANT SELECT ON bronze.* TO 'reader'@'%';
