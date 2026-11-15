"""Régressions des corrections S2 et du refus de repli S5."""
import os
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipelines'))
import s2_adapter
import audit_final


class Corrections(unittest.TestCase):
    def test_population_normalizes_case_accents_spaces(self):
        df = pd.DataFrame({'client_id': ['a'] * 5, 'type_personne': ['souscripteur', ' SOUSCRIPTEUR ', 'souscriptéur', 'assure', None], 'raison_sociale': [None] * 5})
        self.assertEqual(s2_adapter.physical_subscribers(df).tolist(), [True, True, True, False, False])

    def test_date_explicit_or_execution_day(self):
        with patch.dict(os.environ, {'DQ_COMPARISON_DATE': '2026-11-15'}):
            self.assertEqual(s2_adapter.comparison_date(), pd.Timestamp('2026-11-15'))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(s2_adapter.comparison_date(), pd.Timestamp.today().normalize())

    def test_silver_adapter_preserves_roles_and_nature(self):
        df = pd.DataFrame({'source_id': ['a', 'b', 'c'], 'source_systeme': ['crm', 'crm', 'cif'], 'type_personne': ['souscripteur'] * 3, 'nature_personne': ['PP', 'PM', 'PP'], 'pays_iso': ['FR'] * 3, 'telephone_normalise': ['01'] * 3})
        adapted = s2_adapter.silver_clients(df)
        self.assertEqual(adapted.client_id.tolist(), ['a', 'b'])
        self.assertEqual(s2_adapter.physical_subscribers(adapted).tolist(), [True, False])
        self.assertEqual(adapted.pays.tolist(), ['FR', 'FR'])

    def test_historical_metadata_without_certified_catalogue_refused(self):
        with self.assertRaisesRegex(ValueError, 'REPLI_STEWARD_REFUSE'):
            audit_final.historical_steward_policy({'batch_id': 'L1', 'historique': {'mesures': [{'dimension': 'courante'}]}}, {'batch_id': 'L1'})

    def test_both_notebook_age_calculations_share_population(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root / 'notebooks/S2_g02.ipynb').read_text())
        rows = pd.DataFrame({'contrat_id': ['C1', 'C2'], 'souscripteur_id': ['A', 'B'], 'client_id': ['A', 'B'],
                             'type_personne': [' SOUSCRIPTEUR ', 'souscriptéur'], 'raison_sociale': [None, ''],
                             'date_debut': ['2026-01-01'] * 2, 'date_naissance': ['2010-01-01', '1990-01-01']})
        scope = {'pd': pd, 'physical_subscribers': s2_adapter.physical_subscribers,
                 'contrats': rows.copy(), 'diagnostic_rq002': rows.copy(),
                 'DATE_COMPARAISON': pd.Timestamp('2026-11-15'), 'display': lambda value: None}
        for i in (7, 32):
            exec(compile(''.join(notebook['cells'][i]['source']), '<ages>', 'exec'), scope)
        self.assertEqual(int(scope['contrats'].personne_physique.sum()), scope['nb_souscripteurs'])
        self.assertEqual(int((scope['contrats'].age_debut < 18).sum()), len(scope['echecs_debut']))

    def test_complete_certified_history_accepted_and_tampering_refused(self):
        # _history empreinte les lignes B/S/G dans l'ordre id, avant dédoublonnage.
        catalogue = [{'rule_id': 'RQ-001', 'libelle': 'Dates', 'porte': 'B', 'dimension': 'Validité', 'severite': 'BLOQUANTE', 'seuil_min': '100.00'}]
        rows = [{'id': 1, 'rule_id': 'RQ-001', 'couche': 'GOLD', 'table_cible': 'contrat', 'nb_testees': 10, 'nb_echecs': 0}]
        certificate = {'batch_id': 'L1', 'catalogue_sha256': audit_final.s5.digest(catalogue),
                       'history_sha256': audit_final.s5.digest(rows)}
        export = {'batch_id': 'L1', 'catalogue': catalogue,
                  'historique': {'sha256': certificate['history_sha256'], 'mesures': rows}}
        self.assertEqual(audit_final.historical_steward_policy(export, certificate), catalogue)
        rows[0]['nb_echecs'] = 1
        with self.assertRaisesRegex(ValueError, 'altérées'):
            audit_final.historical_steward_policy(export, certificate)

    def history_fixture(self):
        catalogue = [{'rule_id': 'RQ-001', 'libelle': 'Dates', 'dimension': 'Validité', 'porte': 'B', 'severite': 'BLOQUANTE', 'seuil_min': 100}]
        rows = [{'id': i, 'rule_id': 'RQ-001', 'couche': 'GOLD', 'table_cible': 'S5_contrat', 'nb_testees': 10, 'nb_echecs': 2-i} for i in (1, 2)]
        digest = audit_final.s5.digest(rows)
        return {'batch_id': 'L1', 'catalogue': catalogue, 'historique': {'mesures': rows, 'sha256': digest}}, {'batch_id': 'L1', 'catalogue_sha256': audit_final.s5.digest(catalogue), 'history_sha256': digest}

    def test_complete_ordered_duplicate_history_and_deduplicated_export(self):
        export, certificate = self.history_fixture()
        self.assertEqual(audit_final.historical_steward_policy(export, certificate), export['catalogue'])
        export['historique']['mesures'] = export['historique']['mesures'][-1:]
        with self.assertRaisesRegex(ValueError, 'REPLI_STEWARD_REFUSE'):
            audit_final.historical_steward_policy(export, certificate)

    def test_null_malformed_and_extra_layers_refused(self):
        from copy import deepcopy
        valid, certificate = self.history_fixture()
        cases = [None, [], dict(valid, historique=None), dict(valid, catalogue=[None]),
                 dict(valid, historique={'mesures': None}), dict(valid, historique={'mesures': [None]})]
        for layer in ('CRM', 'HACK', None):
            extra = deepcopy(valid)
            extra['historique']['mesures'].append(dict(extra['historique']['mesures'][0], id=3, couche=layer))
            cases.append(extra)
        for export in cases:
            with self.subTest(export=export), self.assertRaisesRegex(ValueError, 'REPLI_STEWARD_REFUSE'):
                audit_final.historical_steward_policy(export, certificate)

    def test_real_steward_fallback_cell_refuses_incomplete_export(self):
        import tempfile
        root = Path(__file__).resolve().parents[1]
        cell = ''.join(json.loads((root/'notebooks/S5_data_steward.ipynb').read_text())['cells'][5]['source'])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'reports').mkdir()
            (Path(directory)/'reports/S5_export_steward.json').write_text(json.dumps({'historique': {'mesures': []}}))
            scope = {'BASE_EST_REFERENCE': False, 'RACINE': directory, 'pd': pd, 'json': json,
                     'audit_final': audit_final, 'certificat': {}, 'regles': pd.DataFrame()}
            with self.assertRaisesRegex(ValueError, 'REPLI_STEWARD_REFUSE'):
                exec(compile(cell, '<steward-fallback>', 'exec'), scope)
            self.assertNotIn('h', scope)

    def test_us10_configuration_and_silver_history(self):
        import tempfile
        from sqlalchemy import create_engine, text
        from unittest.mock import MagicMock
        self.enterContext(patch.dict(sys.modules, {'IPython': MagicMock(), 'IPython.display': MagicMock()}))
        root = Path(__file__).resolve().parents[1]
        cells = json.loads((root/'notebooks/S2_US10_regles_en_tests.ipynb').read_text())['cells']
        # Exécuter la cellule réelle, avec moteur de lecture simulé uniquement.
        for layer, schema, report in [('SILVER', 'silver', 'S2_execution_silver.json'), ('BRONZE', 'bronze', 'S2_execution.json')]:
            with tempfile.TemporaryDirectory() as directory:
                fake = Path(directory); (fake/'pipelines').mkdir(); (fake/'pipelines/s5_engineering.py').touch()
                with patch.dict(os.environ, {'DQ_S2_LAYER': layer}, clear=True), patch('sqlalchemy.create_engine', return_value=MagicMock()), patch('pandas.read_sql', return_value=pd.DataFrame()), patch.object(Path, 'cwd', return_value=fake):
                    scope = {}
                    exec(compile(''.join(cells[1]['source']), '<us10-init>', 'exec'), scope)
                    self.assertEqual((scope['LAYER'], scope['SCHEMA']), (layer, schema))
                    engine = create_engine('sqlite://')
                    with engine.begin() as cx:
                        cx.exec_driver_sql("ATTACH ':memory:' AS dq")
                        cx.exec_driver_sql('CREATE TABLE dq.dq_history(id INTEGER PRIMARY KEY,batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)')
                    scope.update(WRITER=engine, resultats=[{'rule_id': 'RQ-001', 'table_cible': 'contrat', 'lignes': 10, 'anomalies': 0}])
                    exec(compile(''.join(cells[15]['source']), '<us10-history>', 'exec'), scope)
                    with engine.connect() as cx:
                        self.assertEqual(cx.execute(text('SELECT couche FROM dq.dq_history')).scalar_one(), layer)
                    proof = json.loads((fake/'reports'/report).read_text())
                    self.assertEqual(proof['perimetre_source'], {'source_systeme': 'crm'} if layer == 'SILVER' else {})
                    engine.dispose()
        with patch.dict(os.environ, {'DQ_S2_LAYER': 'INVALID'}, clear=True), patch('sqlalchemy.create_engine', return_value=MagicMock()):
            with self.assertRaisesRegex(ValueError, 'DQ_S2_LAYER'):
                exec(compile(''.join(cells[1]['source']), '<us10-invalid>', 'exec'), {})

    def test_validator_forces_layer_and_reports_effective_source(self):
        import importlib.util
        import tempfile
        from unittest.mock import MagicMock
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('validator', root/'scripts/valider_notebooks.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for silver in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                fake = Path(directory); (fake/'notebooks').mkdir()
                import nbformat
                nbformat.write(nbformat.v4.new_notebook(), fake/'notebooks/S2_US10_regles_en_tests.ipynb')
                observed = []
                client = MagicMock()
                client.return_value.execute.side_effect = lambda: observed.append((os.environ['DQ_SCHEMA'], os.environ['DQ_S2_LAYER']))
                args = ['validate', '--notebooks', 'S2_US10_regles_en_tests'] + (['--silver'] if silver else [])
                with patch.object(module, 'ROOT', fake), patch.object(module, 'create_engine', return_value=MagicMock()), patch.object(module, 'NotebookClient', client), patch.object(sys, 'argv', args), patch.dict(os.environ, {'DQ_SCHEMA': 'silver', 'DQ_S2_LAYER': 'SILVER'}, clear=True):
                    module.main()
                report = json.loads(next((fake/'reports/executions').glob('*/validation.json')).read_text())
                self.assertEqual(observed, [('silver', 'SILVER')] if silver else [('bronze', 'BRONZE')])
                self.assertEqual(report['schema_source'], observed[0][0])
                self.assertEqual(report['couche'], observed[0][1])
                self.assertIn('tables', report)
                self.assertTrue(report['rapport_mesures'].endswith('.json'))
