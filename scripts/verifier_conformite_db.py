"""Contrôle MariaDB explicite : lecture du nominal et fixture temporaire supprimée.

Exécuter volontairement avec PyMySQL et PyYAML installés ; aucune découverte CI.
"""
import json, uuid, re
from pathlib import Path
import pymysql, yaml
root = Path(__file__).resolve().parents[1]
out = root / 'reports/executions/conformite_prof_20261115'

def main():
    c = pymysql.connect(host='127.0.0.1', user='root', password='root', port=3306, autocommit=True)
    schema = 'test_conformite_' + uuid.uuid4().hex[:12]
    with c.cursor() as q:
        q.execute('SELECT * FROM dq.certificat_qualite WHERE certificat_id = %s', ('S5-d7c760617b538e9240c8541a4f7',))
        row = dict(zip([d[0] for d in q.description], q.fetchone()))
        row = {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v for k, v in row.items()}
        original = json.loads((root / 'livrables/preuves/S5_certificat_ligne_sql.json').read_text())
        assert row == original, (row, original)
        sql = '\n'.join((line for line in (root / 'queries/S3_US14_client_actif.sql').read_text().splitlines() if not line.startswith('--')))
        for statement in sql.split(';'):
            if statement.strip():
                q.execute(statement)
        nominal = q.fetchone()[0]
        assert nominal == 38049, nominal
        q.execute("SELECT COUNT(*), SUM(cp IS NULL OR cp NOT REGEXP '^[0-9]{5}$') FROM bronze.crm_client WHERE _batch_id='L-2026-10-01' AND pays='FR'")
        pop, bad = q.fetchone()
        q.execute(f'CREATE DATABASE `{schema}`')
        try:
            q.execute(f'CREATE TABLE {schema}.crm_contrat (contrat_id VARCHAR(20),souscripteur_id VARCHAR(20),assure_id VARCHAR(20),code_type VARCHAR(20),_batch_id VARCHAR(30),date_debut VARCHAR(10), date_fin VARCHAR(10),date_derniere_cotisation VARCHAR(10))')
            q.execute(f'CREATE TABLE {schema}.crm_client (client_id VARCHAR(20),_batch_id VARCHAR(30),type_personne VARCHAR(30))')
            q.execute(f"INSERT INTO {schema}.crm_contrat VALUES ('K','X','X','T','LOT_A','2026-01-01','2026-12-31','2026-09-01')")
            q.execute(f"INSERT INTO {schema}.crm_client VALUES ('X','LOT_B','souscripteur')")
            q.execute(f'CREATE TABLE {schema}.crm_type_contrat (code_type VARCHAR(20),_batch_id VARCHAR(30))')
            q.execute(f"INSERT INTO {schema}.crm_type_contrat VALUES ('T','LOT_B')")
            q.execute(f'CREATE TABLE {schema}.crm_sinistre (sinistre_id VARCHAR(20),contrat_id VARCHAR(20),_batch_id VARCHAR(30),date_survenance VARCHAR(10))')
            checks = yaml.safe_load((root / 'soda/checks/bronze_contrat_checks.yml').read_text())['checks for crm_contrat [lot]']

            def query_regle(regle):
                for check in checks:
                    cfg = next(iter(check.values()))
                    if isinstance(cfg, dict) and regle in cfg.get('name', ''):
                        query = next((v for k, v in cfg.items() if k.endswith('query')))
                        return query.replace('bronze.', schema + '.').replace('${BATCH_ID}', 'LOT_A').replace('${REFERENCE_DATE}', '2026-10-01')
            q.execute(query_regle('RQ-011'))
            rq011_autre_lot = sorted(row[0] for row in q.fetchall())
            assert rq011_autre_lot == ['K'], rq011_autre_lot
            q.execute(f"INSERT INTO {schema}.crm_type_contrat VALUES ('T','LOT_A')")
            q.execute(query_regle('RQ-011'))
            rq011_meme_lot = sorted(row[0] for row in q.fetchall())
            assert rq011_meme_lot == [], rq011_meme_lot
            q.execute(query_regle('RQ-012'))
            assert len(q.fetchall()) == 1
            q.execute(query_regle('RQ-013'))
            assert q.fetchone()[0] == 1
            fixture = sql.replace('bronze.', schema + '.').replace('L-2026-10-01', 'LOT_A')
            for st in fixture.split(';'):
                if st.strip():
                    q.execute(st)
            avant = q.fetchone()[0]
            assert avant == 1
            q.execute(f"INSERT INTO {schema}.crm_contrat VALUES ('K','Y','Y','T','LOT_B','2026-01-01','2026-12-31','2026-09-01')")
            for st in fixture.split(';'):
                if st.strip():
                    q.execute(st)
            apres = q.fetchone()[0]
            assert apres == avant
            fixture = fixture.replace('LOT_A', 'LOT_ABSENT')
            for st in fixture.split(';'):
                if st.strip():
                    q.execute(st)
            assert q.fetchone()[0] == 0
            # RQ015/RQ016 : les contrats d’un autre lot ne satisfont pas la relation.
            q.execute(f"INSERT INTO {schema}.crm_client VALUES ('PROSPECT','LOT_A','prospect'), ('SOUSCRIPTEUR','LOT_A','souscripteur')")
            q.execute(f"INSERT INTO {schema}.crm_contrat VALUES ('KP','PROSPECT',NULL,'T','LOT_B','2026-01-01','2026-12-31','2026-09-01'), ('KS','SOUSCRIPTEUR',NULL,'T','LOT_B','2026-01-01','2026-12-31','2026-09-01')")
            checks_client = yaml.safe_load((root / 'soda/checks/bronze_client_checks.yml').read_text())['checks for crm_client [lot]']
            def mesurer_client(regle):
                query = next(v for check in checks_client for cfg in check.values() if isinstance(cfg, dict) and regle in cfg.get('name', '') for k, v in cfg.items() if k.endswith('query'))
                q.execute(query.replace('bronze.', schema + '.').replace('${BATCH_ID}', 'LOT_A'))
                return float(q.fetchone()[0])
            assert mesurer_client('RQ-015') == 0
            assert mesurer_client('RQ-016') == 0
            # Ajouter les cas de jointure après US14 pour conserver sa fixture initiale.
            q.execute(f"INSERT INTO {schema}.crm_contrat VALUES ('AUTRE','Y','Y','T','LOT_B','2026-01-01','2026-12-31','2026-09-01')")
            q.execute(f"INSERT INTO {schema}.crm_sinistre VALUES ('S_AUTRE_LOT','AUTRE','LOT_A','2026-06-01'), ('S_VALIDE','K','LOT_A','2026-06-01'), ('S_AVANT','K','LOT_A','2025-12-31'), ('S_APRES','K','LOT_A','2027-01-01'), ('S_IGNORE','ABSENT','LOT_B','2026-06-01'), ('S_INVALIDE','K','LOT_A','invalide')")
            checks_sinistre = yaml.safe_load((root / 'soda/checks/bronze_sinistre_checks.yml').read_text())['checks for crm_sinistre [lot]']
            rq017 = next(cfg['fail query'] for check in checks_sinistre for cfg in check.values() if isinstance(cfg, dict) and 'RQ-017' in cfg.get('name', ''))
            q.execute(rq017.replace('bronze.', schema + '.').replace('${BATCH_ID}', 'LOT_A'))
            rq017_rejetes = sorted(row[0] for row in q.fetchall())
            assert rq017_rejetes == ['S_APRES', 'S_AUTRE_LOT', 'S_AVANT', 'S_INVALIDE'], rq017_rejetes
            q.execute(f"INSERT INTO {schema}.crm_contrat VALUES ('K_INVALIDE','X','X','T','LOT_A','invalide','2026-12-31','2026-09-01')")
            rq001_condition = next(cfg['fail condition'] for check in checks for cfg in check.values() if isinstance(cfg, dict) and 'RQ-001' in cfg.get('name', ''))
            q.execute(f"SELECT contrat_id FROM {schema}.crm_contrat WHERE _batch_id='LOT_A' AND ({rq001_condition})")
            rq001_rejetes = sorted(row[0] for row in q.fetchall())
            assert rq001_rejetes == ['K_INVALIDE'], rq001_rejetes
            evidence = {'nominal_us14_clients_actifs': nominal, 'rq005_bronze_fr_exact': {'population': pop, 'echecs': int(bad), 'conformite_pct': round(100 * (pop - int(bad)) / pop, 2)}, 'certificat_export_exact': True, 'isolation': {'rq001_date_invalide_rejetee': rq001_rejetes, 'rq015_prospect_contrat_autre_lot': 0, 'rq016_taux_avec_contrat_autre_lot': 0, 'rq011_rejetes_avant_reference_meme_lot': rq011_autre_lot, 'rq011_rejetes_apres_reference_meme_lot': rq011_meme_lot, 'rq017_identifiants_rejetes': rq017_rejetes, 'rq017_identifiant_meme_lot_valide': 'S_VALIDE', 'rq012_reference_autre_lot_refusee': True, 'rq013_reference_autre_lot_refusee': True, 'us14_avant_ajout_autre_lot': avant, 'us14_apres_ajout_autre_lot': apres, 'us14_lot_absent': 0}, 'schema_synthetique_nettoye': schema}
        finally:
            q.execute(f'DROP DATABASE `{schema}`')
    (out / 'verification_db.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(evidence))
if __name__ == '__main__':
    main()
