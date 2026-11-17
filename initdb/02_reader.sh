#!/bin/bash
# Sourcé par l’entrypoint MariaDB après les schémas SQL.
set -e
: "${DQ_READER_PASSWORD:?DQ_READER_PASSWORD requis}"
# Un littéral hexadécimal UTF-8 évite toute interpolation SQL du secret.
reader_password_hex=$(printf '%s' "$DQ_READER_PASSWORD" | od -An -v -tx1 | tr -d ' \n')
docker_process_sql <<SQL
SET SESSION sql_mode = '';
SET @reader_password = CONVERT(0x${reader_password_hex} USING utf8mb4);
SET @reader_sql = CONCAT('CREATE USER IF NOT EXISTS \'reader\'@\'%\' IDENTIFIED BY ', QUOTE(@reader_password));
PREPARE reader_statement FROM @reader_sql;
EXECUTE reader_statement;
DEALLOCATE PREPARE reader_statement;
GRANT SELECT ON cif.* TO 'reader'@'%';
GRANT SELECT ON crm.* TO 'reader'@'%';
GRANT SELECT ON bronze.* TO 'reader'@'%';
SQL
unset reader_password_hex
