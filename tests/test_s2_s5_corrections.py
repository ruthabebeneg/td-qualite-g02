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
        for layer, schema, report in [('GOLD', 'gold', 'S2_execution_gold.json'), ('SILVER', 'silver', 'S2_execution_silver.json'), ('BRONZE', 'bronze', 'S2_execution.json')]:
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
        for layer in ('BRONZE', 'SILVER', 'GOLD'):
            with tempfile.TemporaryDirectory() as directory:
                fake = Path(directory); (fake/'notebooks').mkdir()
                import nbformat
                nbformat.write(nbformat.v4.new_notebook(), fake/'notebooks/S2_US10_regles_en_tests.ipynb')
                observed = []
                client = MagicMock()
                raw_paths = []
                unrelated = fake/'reports/S2_execution_autre_rejeu.json'
                unrelated.parent.mkdir(); unrelated.write_text('preuve antérieure')
                def execute_notebook():
                    observed.append((os.environ['DQ_SCHEMA'], os.environ['DQ_S2_LAYER']))
                    raw = Path(os.environ['DQ_S2_EXECUTION_REPORT'])
                    raw_paths.append(raw)
                    raw.write_text(json.dumps({
                        'history_schema': os.environ['DQ_HISTORY_SCHEMA'],
                        'couche': layer, 'schema': layer.lower(),
                        'source': 'exécution courante du notebook',
                        'mesures': [{'rule_id':'RQ-001','lignes':2,'anomalies':1}],
                        'history_ids': [1]}))
                client.return_value.execute.side_effect = execute_notebook
                args = ['validate', '--notebooks', 'S2_US10_regles_en_tests'] + (['--' + layer.lower()] if layer != 'BRONZE' else [])
                with patch.object(module, 'ROOT', fake), patch.object(module, 'create_engine', return_value=MagicMock()), patch.object(module, 'NotebookClient', client), patch.object(sys, 'argv', args), patch.dict(os.environ, {'DQ_SCHEMA': 'silver', 'DQ_S2_LAYER': 'SILVER'}, clear=True):
                    module.main()
                report = json.loads(next((fake/'reports/executions').glob('*/validation.json')).read_text())
                self.assertEqual(observed, [(layer.lower(), layer)])
                self.assertEqual(report['schema_source'], observed[0][0])
                self.assertEqual(report['couche'], observed[0][1])
                self.assertIn('tables', report)
                self.assertTrue(report['rapport_mesures'].endswith('.json'))
                self.assertEqual(unrelated.read_text(), 'preuve antérieure')
                if layer == 'GOLD':
                    canonical = fake/'reports/S2_execution_gold.json'
                    self.assertEqual(report['rapport_mesures'], str(canonical))
                    proof = json.loads(canonical.read_text())
                    self.assertEqual(proof['history_schema'], report['schema_validation'])
                    self.assertTrue(proof['schema_nettoye'])
                    self.assertEqual(proof['nb_mesures'],1)
                    self.assertEqual(proof['mesures'],[{'rule_id':'RQ-001','lignes':2,'anomalies':1}])
                    self.assertEqual(proof['provenance']['rapport_execute'],raw_paths[0].name)
                    self.assertFalse(raw_paths[0].exists())
                    self.assertNotIn('history_ids',proof)
                else:
                    self.assertTrue(raw_paths[0].exists())

class GoldCorrections(unittest.TestCase):
    def test_age_scope_missing_unknown_pm_and_anniversary(self):
        clients = pd.DataFrame({'cli_id': ['a','b','c','d','e'],
            'nature_personne': ['PP','PM','inconnu',None,'PP'],
            'date_naissance': ['2008-06-02',None,'1990-01-01','1990-01-01',None]})
        contracts = pd.DataFrame({'contrat_id': list('1234567'),
            'cli_souscripteur': ['a','a','b','c','d','e','absent'],
            'date_debut': ['2026-06-01','2026-06-02']+['2026-06-02']*5})
        rows, ok = s2_adapter.gold_age_population(clients, contracts)
        self.assertEqual(rows.contrat_id.tolist(),list('124567'))
        self.assertEqual(ok.tolist(),[False,True,False,False,False,False])

    def test_duplicate_empty_references_fail_and_missing_start(self):
        clients = pd.DataFrame({'cli_id':['a','a','','b'], 'nature_personne':['PP']*4,
                                'date_naissance':['1990-01-01']*4})
        contracts = pd.DataFrame({'cli_souscripteur':['a','','b'], 'date_debut':['2026-01-01','2026-01-01',None]})
        rows, ok = s2_adapter.gold_age_population(clients, contracts)
        self.assertEqual(len(rows),3)
        self.assertEqual(ok.tolist(),[False]*3)

    def test_gold_status_population(self):
        frame = pd.DataFrame({'cli_id':list('abcdef'), 'pays_iso':['FR']*6,
                              'statut_client':['ACTIF','INACTIF','A_REVOIR','ASSURE','PROSPECT','INCONNU']})
        adapted = s2_adapter.gold_clients(frame)
        self.assertEqual(adapted.type_personne.eq('souscripteur').sum(),3)
        self.assertTrue(pd.isna(adapted.type_personne.iloc[-1]))

    def test_validator_cleans_and_restores_environment_on_failure(self):
        import importlib.util
        import tempfile
        from unittest.mock import MagicMock
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('validator_failure', root/'scripts/valider_notebooks.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory); (fake/'notebooks').mkdir()
            import nbformat
            nbformat.write(nbformat.v4.new_notebook(),fake/'notebooks/S2_US10_regles_en_tests.ipynb')
            engine = MagicMock(); client = MagicMock()
            client.return_value.execute.side_effect = RuntimeError('échec injecté')
            initial = {'DQ_SCHEMA':'original','DQ_S2_LAYER':'original','DQ_HISTORY_SCHEMA':'nominal'}
            with patch.object(module,'ROOT',fake), patch.object(module,'create_engine',return_value=engine), patch.object(module,'NotebookClient',client), patch.object(sys,'argv',['validate','--gold']), patch.dict(os.environ,initial,clear=True):
                with self.assertRaisesRegex(RuntimeError,'échec injecté'):
                    module.main()
                self.assertEqual(dict(os.environ),initial)
            sql = [str(call.args[0]) for call in engine.begin.return_value.__enter__.return_value.execute.call_args_list]
            self.assertTrue(any('DROP DATABASE' in query for query in sql))
            report = json.loads(next((fake/'reports/executions').glob('*/validation.json')).read_text())
            self.assertTrue(report['schema_nettoye'])
            self.assertFalse(report['tous_passes'])
            engine.dispose.assert_called_once()


    def test_validator_rejects_simultaneous_layers_before_engine_creation(self):
        import importlib.util
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('validator_exclusive', root/'scripts/valider_notebooks.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with patch.object(module, 'create_engine') as engine, patch.object(sys, 'argv', ['validate', '--gold', '--silver']):
            with self.assertRaises(SystemExit) as error:
                module.main()
            self.assertEqual(error.exception.code, 2)
            engine.assert_not_called()

    def test_real_gold_cells_populations_and_failures(self):
        root = Path(__file__).resolve().parents[1]
        cells = json.loads((root/'notebooks/S2_US10_regles_en_tests.ipynb').read_text())['cells']
        clients = s2_adapter.gold_clients(pd.DataFrame({
            'cli_id': ['a','b','b','',None,'f'],
            'statut_client': ['ACTIF','INACTIF','A_REVOIR','ASSURE','PROSPECT','INCONNU'],
            'pays_iso': ['FR','FRANCE','fr','FR','FR','FR'],
            'telephone': [None,'','   ',None,None,'01'],
            'cp': ['75001','invalide','invalide','75002','75003','75004']}))
        contracts = pd.DataFrame({'contrat_id':['x','x','',None,'y']})
        results = []
        def control(rule, description, rows, condition, table_cible, seuil=1.0):
            condition = pd.Series(condition,index=rows.index).fillna(False)
            results.append((rule,description,len(rows),int((~condition).sum())))
            return rows.loc[~condition].copy()
        scope = {'pd':pd,'clients':clients,'contrats':contracts,'LAYER':'GOLD',
                 'TABLE_CLIENT':'client_unique','TABLE_CONTRAT':'contrat_certifie',
                 'controler':control,'display':lambda value:None}
        for index in (9,10,11,13,16):
            exec(compile(''.join(cells[index]['source']),f'<gold-cell-{index}>','exec'),scope)
        self.assertEqual([(r[0],r[2],r[3]) for r in results],
                         [('RQ-003',3,3),('RQ-005',4,0),('RQ-009',6,1),
                          ('RQ-020',6,4),('RQ-020',5,4)])
        self.assertEqual(results[2][1],'Statut Gold autorisé')
        self.assertEqual(scope['pays_fr'].tolist(),[True,False,False,True,True,True])
        self.assertEqual(scope['cp_invalides_fr'],0)
        for rule in ('001','002','003','005','009','010'):
            scope['anomalies_RQ'+rule] = pd.DataFrame({'rule_id':['RQ-'+rule] if rule in ('002','009') else [],
                                                        'table_cible':['contrat_certifie' if rule=='002' else 'client_unique'] if rule in ('002','009') else []})
        scope['anomalies_RQ020'] = [pd.DataFrame(columns=['rule_id','table_cible'])]
        exec(compile(''.join(cells[17]['source']),'<gold-cell-17>','exec'),scope)
        causes = scope['echantillon'].set_index('rule_id').cause_probable
        self.assertIn('nature, date ou référence',causes['RQ-002'])
        self.assertEqual(causes['RQ-009'],'Statut Gold non autorisé')


    def test_gold_canonical_report_preserved_on_execution_or_cleanup_failure(self):
        import importlib.util
        import tempfile
        from unittest.mock import MagicMock
        import nbformat
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('validator_preserve',root/'scripts/valider_notebooks.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for fail_cleanup in (False, True):
            with self.subTest(fail_cleanup=fail_cleanup), tempfile.TemporaryDirectory() as directory:
                fake = Path(directory); (fake/'notebooks').mkdir(); (fake/'reports').mkdir()
                nbformat.write(nbformat.v4.new_notebook(),fake/'notebooks/S2_US10_regles_en_tests.ipynb')
                canonical = fake/'reports/S2_execution_gold.json'; canonical.write_text('preuve à préserver')
                raw_paths = []
                engine = MagicMock(); client = MagicMock()
                def execute_notebook():
                    raw = Path(os.environ['DQ_S2_EXECUTION_REPORT']); raw_paths.append(raw)
                    raw.write_text(json.dumps({'mesures':[]}))
                    self.assertEqual(canonical.read_text(),'preuve à préserver')
                    if not fail_cleanup:
                        raise RuntimeError('échec notebook')
                def execute_sql(statement):
                    if 'DROP DATABASE' in str(statement):
                        self.assertEqual(canonical.read_text(),'preuve à préserver')
                        if fail_cleanup:
                            raise RuntimeError('échec nettoyage')
                engine.begin.return_value.__enter__.return_value.execute.side_effect = execute_sql
                client.return_value.execute.side_effect = execute_notebook
                with patch.object(module,'ROOT',fake), patch.object(module,'create_engine',return_value=engine), patch.object(module,'NotebookClient',client), patch.object(sys,'argv',['validate','--gold']):
                    with self.assertRaisesRegex(RuntimeError,'échec'):
                        module.main()
                self.assertEqual(canonical.read_text(),'preuve à préserver')
                self.assertTrue(raw_paths[0].exists())

    def test_real_gold_ge_eight_suites_roundtrip_and_age_diagnostics(self):
        import tempfile
        root = Path(__file__).resolve().parents[1]
        cells = json.loads((root/'notebooks/S2_US10_regles_en_tests.ipynb').read_text())['cells']
        clients = s2_adapter.gold_clients(pd.DataFrame({
            'cli_id':['a','b','c','d','e','f','f','','z'],
            'nature_personne':['PP','PP','PM','INCONNUE','PP','PP','PP','PP','PP'],
            'date_naissance':['1990-01-01','2008-06-02',None,'1990-01-01',None]+['1990-01-01']*4,
            'statut_client':['ACTIF','INACTIF','A_REVOIR','ASSURE','PROSPECT','ACTIF','ACTIF','ASSURE','INCONNU'],
            'telephone':[None,'','  ','01','01','01','01','01','01'],
            'pays_iso':['FR','FRANCE','fr']+['FR']*6,
            'cp':['invalide','invalide','invalide']+['75001']*6}))
        contracts = pd.DataFrame({
            'contrat_id':['x','x','',None,'y','q','r','s','t','u','n'],
            'cli_souscripteur':['a','b','c','d','e','f','absent','z','b','','a'],
            'date_debut':['2026-06-01']*3+[None]+['2026-06-01']*4+['2026-06-02','2026-06-01',None],
            'date_fin':['2027-06-01','2026-06-01',None]+['2027-06-01']*8,
            'duree_garantie_mois':[12,13,24,36,60,None,12,12,12,12,12]})
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GE_USAGE_STATS':'false'}):
            suites = Path(directory)/'expectations'; suites.mkdir()
            scope = {'pd':pd,'json':json,'clients':clients,'contrats':contracts,
                     'LAYER':'GOLD','SCHEMA':'gold','PERIMETRE_SOURCE':{},'SUITES':suites,
                     'TABLE_CLIENT':'client_unique','TABLE_CONTRAT':'contrat_certifie',
                     'gold_age_population':s2_adapter.gold_age_population,
                     'display':lambda value:None}
            for index in range(6,14):
                exec(compile(''.join(cells[index]['source']),f'<real-ge-gold-{index}>','exec'),scope)
            expected = [('RQ-001',11,4),('RQ-002',10,7),('RQ-003',5,3),('RQ-005',7,1),
                        ('RQ-009',9,1),('RQ-010',11,2),('RQ-020',9,3),('RQ-020',11,4)]
            self.assertEqual([(m['rule_id'],m['lignes'],m['anomalies']) for m in scope['resultats']],expected)
            self.assertEqual(len(list(suites.glob('*/*.json'))),8)
            for measurement in scope['resultats']:
                meta = measurement['expectation_meta']
                self.assertEqual((meta['couche'],meta['schema']),('GOLD','gold'))
                saved = json.loads((suites/measurement['table_cible']/(measurement['rule_id']+'.json')).read_text())
                self.assertEqual(saved['expectations'][0]['meta'],meta)
                # controler a sauvegardé/rechargé la suite avant de calculer ce résultat GE.
                self.assertFalse(measurement['seuil_respecte'])
            non_evaluable = scope['non_evaluables_RQ002']
            self.assertEqual(len(non_evaluable),6)
            self.assertNotIn(1,non_evaluable.index)  # mineur évalué : anomalie, pas donnée absente
            self.assertIn(1,scope['anomalies_RQ002'].index)
            self.assertNotIn(2,scope['anomalies_RQ002'].index)  # PM exclue
