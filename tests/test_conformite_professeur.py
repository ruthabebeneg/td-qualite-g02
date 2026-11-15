"""Contrôles ciblés sans base, Docker ou dépendance graphique."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ConformiteProfesseurTests(unittest.TestCase):
    def test_bronze_toutes_lectures_metier_filtrent_le_lot(self):
        for table in ('client', 'contrat', 'sinistre'):
            config = yaml.safe_load((ROOT / f'soda/checks/bronze_{table}_checks.yml').read_text())
            self.assertEqual(config[f'filter crm_{table} [lot]']['where'], "_batch_id = '${BATCH_ID}'")
            checks = config[f'checks for crm_{table} [lot]']
            self.assertIn('row_count > 0', checks[0])
            for check in checks:
                cfg = next(iter(check.values()))
                for key, query in cfg.items():
                    if key.endswith('query'):
                        self.assertNotRegex(query, r'\b(?:FROM|JOIN) (?:client|contrat|sinistre|type_contrat)\b')
                        accesses = re.findall(r'FROM bronze\.crm_\w+([^)]*)', query)
                        self.assertTrue(accesses)
                        for condition in accesses:
                            self.assertIn("WHERE _batch_id = '${BATCH_ID}'", condition)

    def test_us14_autonome_identique_au_notebook(self):
        sql = (ROOT / 'queries/S3_US14_client_actif.sql').read_text()
        sql = sql[sql.index('SELECT COUNT'):].strip().rstrip(';')
        notebook = json.loads((ROOT / 'notebooks/S3_g02.ipynb').read_text())
        source = ''.join(notebook['cells'][17]['source'])
        requete = source.split('sql_client_actif = """')[1].split('"""')[0]
        requete = requete.replace(':b', '@batch_id').replace(':date_reference', '@date_reference')
        self.assertEqual(' '.join(sql.split()), ' '.join(requete.split()))

    def test_sorties_s3_vingt_lignes_metier_et_aucune_erreur(self):
        notebook = json.loads((ROOT / 'notebooks/S3_g02.ipynb').read_text())
        lignes = 0
        for index, cell in enumerate(notebook['cells']):
            for output in cell.get('outputs', []):
                self.assertNotEqual(output['output_type'], 'error')
                if index in (8, 10, 12):
                    html = ''.join(output.get('data', {}).get('text/html', []))
                    if html:
                        lignes += len(re.findall('<tr', html)) - 1
        self.assertEqual(lignes, 20)

    def test_demo_us30_mesure_reellement_plateau_puis_progression(self):
        spec = importlib.util.spec_from_file_location('demo_us30', ROOT / 'scripts/demo_us30.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        resultat = module.demonstrer()
        self.assertEqual([m['echecs'] for m in resultat['mesures']], [2, 2, 0])
        self.assertEqual([m['conformite_pct'] for m in resultat['mesures']], [50, 50, 100])
        self.assertEqual(resultat['effet_sur_certificat'], 'aucun')

    def test_bronze_parametres_obligatoires_avant_execution(self):
        commande = [sys.executable, str(ROOT / 'soda/run_scan.py'), '-d', 'bronze', '-c', 'absent.yml']
        for variables in ([], ['-v', "BATCH_ID=lot' OR 1=1", '-v', 'REFERENCE_DATE=2026-10-01'],
                          ['-v', 'BATCH_ID=LOT_A', '-v', 'REFERENCE_DATE=2026-13-01'],
                          ['-v', 'BATCH_ID=LOT_A', '-v', 'REFERENCE_DATE=20261001'],
                          ['-v', 'BATCH_ID=LOT_A', '-v', 'REFERENCE_DATE=2026-W40-4']):
            retour = subprocess.run(commande + variables + ['absent.yml'], capture_output=True, text=True)
            self.assertEqual(retour.returncode, 2)
            self.assertIn('Bronze exige', retour.stderr)

    def test_preuve_scan_bronze_sans_erreur_technique(self):
        resultat = json.loads((ROOT / 'reports/executions/conformite_prof_20261115/soda_bronze.json').read_text())
        self.assertFalse(resultat['hasErrors'])
        outcomes = [check['outcome'] for check in resultat['checks']]
        self.assertEqual({value: outcomes.count(value) for value in set(outcomes)}, {'pass': 16, 'warn': 1, 'fail': 10})

    def test_preuves_soda_liees_aux_fichiers_livres(self):
        dossier = ROOT / 'reports/executions/conformite_prof_20261115'
        manifeste = json.loads((dossier / 'soda_provenance.json').read_text())
        self.assertEqual(manifeste['soda_version'], '3.3.5')
        attendus = {'soda/configuration.yml'} | {
            f'soda/checks/{prefix}{table}_checks.yml'
            for prefix in ('', 'bronze_') for table in ('client', 'contrat', 'sinistre')
        }
        self.assertEqual(set(manifeste['fichiers_sha256']), attendus)
        for fichier, empreinte in manifeste['fichiers_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / fichier).read_bytes()).hexdigest(), empreinte, fichier)
        for scan in manifeste['scans'].values():
            self.assertEqual(hashlib.sha256((ROOT / scan['resultats']).read_bytes()).hexdigest(), scan['sha256'])
        self.assertEqual(set(manifeste['referentiels']), {'silver.ref_pays', 'silver.ref_ban'})

    def test_lot_absent_refuse_par_les_trois_presences(self):
        dossier = ROOT / 'reports/executions/conformite_prof_20261115'
        resume = json.loads((dossier / 'soda_bronze_lot_absent_resume.json').read_text())
        self.assertNotEqual(resume['code_retour'], 0)
        self.assertEqual(len(resume['presences_lot']), 3)
        for check in resume['presences_lot']:
            self.assertEqual(check['outcome'], 'fail')
            self.assertEqual(check['valeur'], 0)

    def test_export_certificat_sql_complet(self):
        ligne = json.loads((ROOT / 'livrables/preuves/S5_certificat_ligne_sql.json').read_text())
        self.assertEqual((ligne['signataire'], ligne['decision'], ligne['nb_bloquantes_testees'], ligne['nb_bloquantes_ok']),
                         ('Ruth', 'GO', 59, 59))
        certificat = json.loads((ROOT / 'reports/S5_certificat_final.json').read_text())
        self.assertEqual(ligne['certificat_id'], certificat['certificat_id'])


if __name__ == '__main__':
    unittest.main()
