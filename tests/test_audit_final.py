"""Régressions des constats C17–C30, sans accès aux bases nominales."""
import ast
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import sys
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipelines'))
import audit_final
import s5_engineering as s5


def notebook(name):
    return json.loads((ROOT / 'notebooks' / f'{name}.ipynb').read_text())


def failed_query(filename, rule):
    checks = yaml.safe_load((ROOT / 'soda/checks' / filename).read_text())
    for group in checks.values():
        for check in group:
            config = check.get('failed rows', {})
            if config.get('name', '').startswith(rule):
                return config.get('fail query'), config.get('fail condition')
    raise AssertionError(rule)


class SodaRegression(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript("ATTACH ':memory:' AS silver; ATTACH ':memory:' AS gold;")

    def test_rq009_null_and_domain(self):
        self.db.executescript("CREATE TABLE client(client_id,type_personne); INSERT INTO client VALUES('a',NULL),('b','client'),('c','prosp.'),('d','assuré');")
        query, _ = failed_query('client_checks.yml', 'RQ-009')
        self.assertEqual(self.db.execute(query).fetchall(), [('a',), ('b',)])

    def test_rq007_missing_unknown_known(self):
        self.db.executescript("CREATE TABLE client(client_id,pays); CREATE TABLE silver.ref_pays(code_pays); INSERT INTO silver.ref_pays VALUES('FR'); INSERT INTO client VALUES('a',NULL),('b','XX'),('c','FR');")
        query, _ = failed_query('client_checks.yml', 'RQ-007')
        self.assertEqual(self.db.execute(query).fetchall(), [('a',), ('b',)])

    def test_rq001_missing_equal_inverted_valid(self):
        self.db.executescript("CREATE TABLE contrat(id,date_debut,date_fin); INSERT INTO contrat VALUES(1,NULL,'2026-01-02'),(2,'2026-01-01',NULL),(3,'2026-01-01','2026-01-01'),(4,'2026-01-02','2026-01-01'),(5,'2026-01-01','2026-01-02');")
        _, condition = failed_query('contrat_checks.yml', 'RQ-001')
        self.assertEqual(self.db.execute('SELECT id FROM contrat WHERE '+condition).fetchall(), [(1,), (2,), (3,), (4,)])

    def test_rq019_distinct_cli_same_person_and_separate_batches(self):
        self.db.executescript('''
          CREATE TABLE silver.client(silver_row_id,_batch_id,nature_personne,identite_normalisee,prenom_normalise,date_naissance,cp,adresse_normalisee);
          CREATE TABLE gold.xref_identifiants(silver_row_id,cli_id);
          CREATE TABLE gold.client_unique(cli_id,_batch_id,nom_reference,cp,date_naissance,telephone,email);
          INSERT INTO silver.client VALUES(1,'L1','PP','DUPONT','ALICE','1990-01-01','75001','RUE A'),(2,'L1','PP','DUPONT','ALICE','1990-01-01','75001','RUE A');
          INSERT INTO gold.xref_identifiants VALUES(1,'CLI1'),(2,'CLI2');
          INSERT INTO gold.client_unique VALUES('CLI1','L1','DUPONT ALICE','75001','1990-01-01','0123456789','a@example.org'),('CLI2','L1','DUPONT ALICE','75001','1990-01-01','0123456789','a@example.org');
        ''')
        query, _ = failed_query('client_unique_checks.yml', 'RQ-019')
        collisions = self.db.execute(query).fetchall()
        self.assertEqual({r[0] for r in collisions}, {'identites_PP','signature_nom_cp_naissance_tel','signature_nom_email'})
        self.assertTrue(all(r[2] == 2 for r in collisions))
        self.db.execute("UPDATE gold.client_unique SET _batch_id='L2' WHERE cli_id='CLI2'")
        self.assertEqual(self.db.execute(query).fetchall(), [])

    def test_ban_no_permissive_threshold(self):
        checks = yaml.safe_load((ROOT/'soda/checks/sinistre_checks.yml').read_text())['checks for sinistre']
        metric = next(c['taux_erreur_adresse'] for c in checks if 'taux_erreur_adresse' in c)
        self.assertEqual(metric['fail'], 'when > 0')
        self.assertNotIn('warn', metric)


class NotebookRegression(unittest.TestCase):
    def test_us09_explicit_batch_calendar_boundary(self):
        import pandas as pd
        n = notebook('US-09_client_actif')
        initialization = ast.parse(''.join(n['cells'][0]['source']))
        # Charger uniquement les paramètres purs ; aucune connexion DB.
        selected = [node for node in initialization.body if isinstance(node, ast.Assign)
                    and all(isinstance(t, ast.Name) and t.id in {'BATCH','REFERENCE_DATE','ref','cotisation'} for t in node.targets)]
        import os
        with patch.dict(os.environ, {'DQ_BATCH':'L-2026-05-31','DQ_REFERENCE_DATE':'2026-05-31'}):
            scope = {'pd':pd, 'os':os}
            exec(compile(ast.Module(body=selected,type_ignores=[]), '<params>', 'exec'), scope)
        self.assertEqual(scope['cotisation'], pd.Timestamp('2026-02-28'))
        # Exécuter la véritable connexion/query et les calculs sur deux lots SQL.
        from sqlalchemy import create_engine, event
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as cx:
            cx.exec_driver_sql("ATTACH ':memory:' AS bronze")
            cx.exec_driver_sql("CREATE TABLE bronze.crm_contrat(souscripteur_id,date_debut,date_fin,date_derniere_cotisation,_batch_id)")
            cx.exec_driver_sql("INSERT INTO bronze.crm_contrat VALUES ('A','2025-01-01','2027-01-01','2026-05-01','L-2026-05-31'),('B','2025-01-01','2027-01-01','2026-02-01','L-2026-05-31'),('OTHER','2025-01-01','2027-01-01','2026-05-01','L-OTHER')")
        transmitted=[]
        event.listen(engine,'before_cursor_execute',lambda cx,cursor,sql,params,context,many:transmitted.append(params))
        with patch.dict(os.environ, {'DQ_BATCH':'L-2026-05-31','DQ_REFERENCE_DATE':'2026-05-31'}), patch('sqlalchemy.create_engine',return_value=engine):
            scope={}
            exec(compile(''.join(n['cells'][0]['source']),'<us09-init>','exec'),scope)
            exec(compile(''.join(n['cells'][3]['source']),'<us09-calcul>','exec'),scope)
        self.assertEqual(set(scope['contrat'].souscripteur_id),{'A','B'})
        self.assertEqual((scope['n_commerciale'],scope['n_sinistres'],scope['n_risques']),(2,2,1))
        self.assertEqual(transmitted,[('L-2026-05-31',)])

    def test_s4_connection_closed_after_construction_exception(self):
        n = notebook('S4_g02')
        tree = ast.parse(''.join(n['cells'][1]['source']))
        cleanup = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='liberer_verrou_s4')
        class Connection:
            closed = False
            released = False
            def execute(self, query): self.released = True
            def close(self): self.closed = True
        connection = Connection()
        scope = {'S4_LOCK':connection,'text':lambda s:s}
        exec(compile(ast.Module(body=[cleanup],type_ignores=[]),'<cleanup>','exec'),scope)
        wrapped = ast.parse(''.join(n['cells'][5]['source']))
        wrapped.body[0].body = [ast.Raise(exc=ast.Call(func=ast.Name(id='RuntimeError',ctx=ast.Load()),args=[],keywords=[]),cause=None)]
        ast.fix_missing_locations(wrapped)
        with self.assertRaises(RuntimeError): exec(compile(wrapped,'<failure>','exec'),scope)
        self.assertTrue(connection.released)
        self.assertTrue(connection.closed)
        self.assertIsNone(scope['S4_LOCK'])

    def test_frequency_survival_can_choose_obsolete_valid_phone(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from audit_survie import demonstrate
        result = demonstrate()
        self.assertTrue(result['synthetique'])
        self.assertTrue(result['erreur_fixture_demontree'])
        self.assertNotEqual(result['valeur_retenue'], result['verite_fixture']['telephone_courant'])

    def test_reference_checks_content_history_configuration(self):
        gold={'sha256':'gold','tables':{'client_unique':{'lignes':10,'sha256':'a'}}}
        from datetime import datetime
        history={'sha256':'history'}; manifest={'configuration_sha256':'config', 'modifie_le':datetime(2026,1,1)}; catalogue=[]
        cert={'batch_id':'L1','gold':gold,'history_sha256':'history','manifeste':{'configuration_sha256':'config', 'modifie_le':'2026-01-01 00:00:00'},
              'catalogue_sha256':s5.digest(catalogue),'politique_sha256':'policy'}
        with patch.multiple(s5, fingerprint_gold=lambda *a:gold, _history=lambda *a:history,
                            _manifest=lambda *a:manifest, _catalogue=lambda *a:catalogue,
                            policy_fingerprint=lambda *a:'policy'):
            self.assertTrue(audit_final.reference_state(None,'L1',cert)['identique'])
            for field,value in [('gold',{'sha256':'other','tables':{'client_unique':{'lignes':10,'sha256':'b'}}}),('history_sha256','other'),('manifeste',{'configuration_sha256':'other'})]:
                changed=deepcopy(cert);changed[field]=value
                self.assertFalse(audit_final.reference_state(None,'L1',changed)['identique'])

    def test_existing_publication_verified_without_sql_mutation(self):
        expected = {'lignes':2,'sha256':'same','colonnes':['id']}
        gold = {'sha256':'all','tables':{src:expected for src,_ in s5.MAPPING}}
        proof = {'batch_id':'L1','decision':'GO','owner':{'name':'fixture'}}
        certificate = dict(proof, certificat_id='CERT', preuve_sha256=s5.digest(proof))
        state = {'identique':True,'gold':gold,'historique':{'sha256':'history'},'manifeste':{}}
        journal_proof={'batch_id':'L1','certificat_id':'CERT','empreinte_gold':'all','publication_id':'PUB',
                       'reconciliation':[{'table_gold':src,'table_cible':dst,'gold':expected,'cible':expected,'ecart':0} for src,dst in s5.MAPPING]}
        def rows(cx, query, params):
            if 's5_certification' in query:
                return [{'preuve':json.dumps(proof),'preuve_sha256':s5.digest(proof)}]
            if 'certificat_qualite' in query:
                return [{'decision':'GO','batch_id':'L1','empreinte_gold':'all'}]
            if 's5_publication' in query:
                return [{'publication_id':'PUB','batch_id':'L1','certificat_id':'CERT','empreinte_gold':'all','preuve':json.dumps(journal_proof)}]
            raise AssertionError(query)
        @contextmanager
        def coherent(engine):
            yield object()  # Aucun execute SQL mutateur disponible dans ce scénario.
        with patch.object(audit_final,'reference_state',return_value=state), patch.multiple(
                s5, coherent_connection=coherent, columns=lambda *a:['id'],
                fingerprint_table=lambda *a:expected, rows=rows, owner_valid=lambda *a:True,
                _integrity=lambda *a,**kw:{}):
            result = audit_final.published_state(None,'L1',certificate)
            self.assertEqual(result['ecritures'],0)
            self.assertEqual(result['publication'],'DEJA_PUBLIEE_VERIFIEE')
            self.assertEqual(result['publication_id'],'PUB')
            journal_proof['reconciliation'][0]['ecart']=1
            with self.assertRaisesRegex(s5.PublicationRefusee,'PREUVE_PUBLICATION_ALTEREE'):
                audit_final.published_state(None,'L1',certificate)
            journal_proof['reconciliation'][0]['ecart']=0
            corrupted=deepcopy(certificate);corrupted['owner']={'name':'altered'}
            with self.assertRaisesRegex(s5.PublicationRefusee,'PREUVE_CERTIFICAT_ALTEREE'):
                audit_final.published_state(None,'L1',corrupted)
            with patch.object(s5,'fingerprint_table',return_value=dict(expected,sha256='different')):
                with self.assertRaisesRegex(s5.PublicationRefusee,'RQ025_ECART_CONTENU'):
                    audit_final.published_state(None,'L1',certificate)

    def test_steward_dimension_summary_accepts_history_with_dimension(self):
        import pandas as pd
        history = pd.DataFrame([
            {'rule_id':'RQ-001','dimension':'ancienne étiquette','couche':'BRONZE','nb_testees':100,'nb_echecs':10},
            {'rule_id':'RQ-002','dimension':'ancienne étiquette','couche':'BRONZE','nb_testees':50,'nb_echecs':5},
            {'rule_id':'RQ-001','dimension':'ancienne étiquette','couche':'GOLD','nb_testees':80,'nb_echecs':0},
        ])
        rules = pd.DataFrame([
            {'rule_id':'RQ-001','dimension':'Validité'},
            {'rule_id':'RQ-002','dimension':'Validité'},
        ])
        displayed=[]
        scope={'pd':pd,'h':history,'regles':rules,'display':displayed.append}
        cell=''.join(notebook('S5_data_steward')['cells'][7]['source'])
        exec(compile(cell,'<steward-dimensions>','exec'),scope)
        summary=scope['courbe']
        self.assertEqual(list(summary.index),['Validité'])
        self.assertEqual(summary.loc['Validité','BRONZE'],90.0)
        self.assertEqual(summary.loc['Validité','GOLD'],100.0)
        self.assertTrue(pd.isna(summary.loc['Validité','SILVER']))
        self.assertEqual(scope['dim'].loc[('Validité','BRONZE'),'nb_testees'],150)
        self.assertEqual(len(displayed),1)

    def test_steward_no_cross_cli_signature_handles_empty_residuals(self):
        import pandas as pd
        import io
        from contextlib import redirect_stdout
        rows = pd.DataFrame([
            {'cli_id':'CLI-1','source_systeme':'crm','source_id':'A',
             'identite_normalisee':'DUPONT','prenom_normalise':'ALICE','date_naissance':'1990-01-01',
             'cp':'75001','telephone_normalise':'0123456789','email_normalise':'a@example.org'},
            {'cli_id':'CLI-1','source_systeme':'cif','source_id':'B',
             'identite_normalisee':'DUPONT','prenom_normalise':'ALICE','date_naissance':'1990-01-01',
             'cp':'75001','telephone_normalise':'0123456789','email_normalise':'a@example.org'},
            {'cli_id':'CLI-2','source_systeme':'crm','source_id':'C',
             'identite_normalisee':'MARTIN','prenom_normalise':'BOB','date_naissance':'1980-02-02',
             'cp':'69001','telephone_normalise':None,'email_normalise':None},
        ])
        cell=''.join(notebook('S5_data_steward')['cells'][15]['source'])
        # Deux identités conformes, puis population complètement vide.
        for fixture in (rows,rows.head(0)):
            with self.subTest(population=len(fixture)):
                displayed=[]; calls=[]
                def query(sql, **params):
                    calls.append(params)
                    return fixture.copy()
                scope={'pd':pd,'BASE_EST_REFERENCE':True,'LOT':'LOT-FIXTURE',
                       'q':query,'display':displayed.append}
                output=io.StringIO()
                with redirect_stdout(output):
                    exec(compile(cell,'<steward-signatures>','exec'),scope)
                self.assertEqual(calls,[{'lot':'LOT-FIXTURE'}])
                self.assertTrue(scope['res'].empty)
                self.assertIsInstance(scope['classes'],pd.Series)
                self.assertTrue(scope['classes'].empty)
                self.assertTrue(scope['exemple'].empty)
                self.assertIn('RQ-019 conforme',displayed[0])
                self.assertIn('Signatures PP sur plusieurs CLI : 0',output.getvalue())

    def test_empty_published_target_refused(self):
        @contextmanager
        def coherent(engine): yield object()
        with patch.multiple(s5,coherent_connection=coherent,columns=lambda *a:['id'],
                            fingerprint_table=lambda *a:{'lignes':0},rows=lambda *a:[{'publication_id':'PUB'}]):
            with self.assertRaisesRegex(s5.PublicationRefusee,'CIBLE_PUBLIEE_VIDE'):
                audit_final.published_state(None,'L1',{})
            with patch.object(s5,'rows',return_value=[]):
                self.assertIsNone(audit_final.published_state(None,'L1',{}))

    def test_s4_reinitialization_releases_previous_connection(self):
        tree=ast.parse(''.join(notebook('S4_g02')['cells'][1]['source']))
        reset=next(node for node in tree.body if isinstance(node,ast.If) and 'S4_LOCK' in ast.unparse(node.test))
        class Connection:
            closed=False
            released=False
            def execute(self,statement): self.released=True
            def close(self): self.closed=True
        connection=Connection()
        scope={'S4_LOCK':connection,'text':lambda sql:sql}
        exec(compile(ast.Module(body=[reset],type_ignores=[]),'<s4-reset>','exec'),scope)
        self.assertTrue(connection.released)
        self.assertTrue(connection.closed)
        self.assertIsNone(scope['S4_LOCK'])

    def test_us11_export_preserves_human_annotations(self):
        import tempfile
        import pandas as pd
        cell=''.join(notebook('S2_US11_lignes_en_echec')['cells'][5]['source'])
        for annotation in ('','vérifié sur pièce'):
            with self.subTest(annotation=annotation), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                (root/'pipelines').mkdir()
                (root/'pipelines/s5_engineering.py').touch()
                (root/'livrables/preuves').mkdir(parents=True)
                path=root/'livrables/preuves/S2_US11_echantillon_commente.csv'
                previous=pd.DataFrame([{'rule_id':'RQ-003','cause_confirmee':annotation,'commentaire_analyse':''}])
                previous.to_csv(path,sep=';',index=False,encoding='utf-8-sig')
                original=path.read_bytes()
                sample=pd.DataFrame([{'rule_id':'RQ-009','cause_confirmee':'','commentaire_analyse':''}])
                scope={'pd':pd,'echecs':sample.copy(),'echantillon':sample.copy()}
                with patch.object(Path,'cwd',return_value=root):
                    if annotation:
                        with self.assertRaisesRegex(RuntimeError,'Analyse humaine existante'):
                            exec(compile(cell,'<export>','exec'),scope)
                        self.assertEqual(path.read_bytes(),original)
                        self.assertFalse((path.parent/'S2_US11_echecs_complets.csv').exists())
                    else:
                        exec(compile(cell,'<export>','exec'),scope)
                        self.assertEqual(pd.read_csv(path,sep=';').rule_id.tolist(),['RQ-009'])
                        self.assertTrue((path.parent/'S2_US11_echecs_complets.csv').exists())

    def test_us11_factual_findings_distinguish_values_and_no_human_confirmation(self):
        import pandas as pd
        rows=pd.DataFrame([
            {'rule_id':'RQ-003','telephone':None},
            {'rule_id':'RQ-003','telephone':''},
            {'rule_id':'RQ-003','telephone':'   '},
            {'rule_id':'RQ-001','date_debut':'2026-01-02','date_fin':'2026-01-01'},
            {'rule_id':'RQ-002','date_debut':'2026-01-01','date_naissance':'2010-01-02'},
            {'rule_id':'RQ-005','pays':'FR','cp':'7500'},
            {'rule_id':'RQ-009','type_personne':'client'},
            {'rule_id':'RQ-010','duree_garantie_mois':15},
        ])
        scope={'pd':pd,'echecs':rows.copy(),'echantillon':rows.copy(),'display':lambda value:None}
        exec(compile(''.join(notebook('S2_US11_lignes_en_echec')['cells'][3]['source']),'<facts>','exec'),scope)
        result=scope['echantillon']
        facts=result.constat_factuel_automatique.tolist()
        self.assertEqual(facts[:3],['telephone=NULL','telephone=vide','telephone=blanc'])
        self.assertIn('2026-01-02',facts[3]);self.assertIn('2026-01-01',facts[3])
        self.assertIn('âge au début=15',facts[4])
        self.assertIn('7500',facts[5]);self.assertIn('client',facts[6]);self.assertIn('15',facts[7])
        self.assertTrue(result.cause_confirmee.eq('').all())
        self.assertTrue(result.commentaire_analyse.eq('').all())

    def test_s2_custom_read_write_settings_and_unique_clients(self):
        import os
        from sqlalchemy import create_engine
        engine=create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as cx:
            cx.exec_driver_sql("ATTACH ':memory:' AS custom_source")
            cx.exec_driver_sql('CREATE TABLE custom_source.custom_clients(client_id,type_personne,raison_sociale,date_naissance,_batch_id)')
            cx.exec_driver_sql("INSERT INTO custom_source.custom_clients VALUES('DUP','souscripteur',NULL,'1990-01-01','LOT'),('DUP','souscripteur',NULL,'1990-01-01','LOT'),('UNIQUE','souscripteur',NULL,'1991-01-01','LOT'),('UNIQUE','souscripteur',NULL,'2000-01-01','OTHER')")
            cx.exec_driver_sql('CREATE TABLE custom_source.custom_contracts(contrat_id,souscripteur_id,date_debut,_batch_id)')
            cx.exec_driver_sql("INSERT INTO custom_source.custom_contracts VALUES('C1','DUP','2026-01-01','LOT'),('C2','UNIQUE','2026-01-01','LOT'),('C3','UNIQUE','2026-01-01','OTHER')")
        writer=object(); urls=[]
        def connect(url):
            urls.append(url)
            return engine if url=='fixture-reader' else writer
        settings={'DQ_BATCH':'LOT','DQ_COMPARISON_DATE':'2026-06-15','DQ_DATABASE_URL':'fixture-reader',
                  'DQ_WRITE_DATABASE_URL':'fixture-writer','DQ_SCHEMA':'custom_source',
                  'DQ_TABLE_CLIENT':'custom_clients','DQ_TABLE_CONTRAT':'custom_contracts'}
        n=notebook('S2_g02');scope={'display':lambda value:None}
        with patch.dict(os.environ,settings),patch('sqlalchemy.create_engine',side_effect=connect):
            exec(compile(''.join(n['cells'][1]['source']),'<s2-init>','exec'),scope)
            exec(compile(''.join(n['cells'][5]['source']),'<s2-join>','exec'),scope)
        self.assertEqual(urls,['fixture-reader','fixture-writer'])
        self.assertIs(scope['READER'],engine);self.assertIs(scope['WRITER'],writer)
        self.assertEqual(str(scope['DATE_COMPARAISON'].date()),'2026-06-15')
        contracts=scope['contrats'].set_index('contrat_id')
        self.assertEqual(set(contracts.index),{'C1','C2'})
        self.assertTrue(__import__('pandas').isna(contracts.loc['C1','client_id']))
        self.assertEqual(contracts.loc['C2','date_naissance'],'1991-01-01')

    def test_us15_selects_exact_us10_insert_ids_and_rejects_wrong_scope(self):
        import os,tempfile
        import pandas as pd
        from sqlalchemy import create_engine,text
        engine=create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as cx:
            cx.exec_driver_sql("ATTACH ':memory:' AS history_fixture")
            cx.exec_driver_sql("CREATE TABLE history_fixture.dq_history(id INTEGER PRIMARY KEY AUTOINCREMENT,batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs,taux_conformite AS (100.0*(nb_testees-nb_echecs)/nb_testees),mesure_le DEFAULT CURRENT_TIMESTAMP)")
        expected=[(r,'contracts') for r in ('RQ-001','RQ-002','RQ-010','RQ-020')]+[(r,'clients') for r in ('RQ-003','RQ-005','RQ-009','RQ-020')]
        results=[{'rule_id':r,'table_cible':t,'lignes':100,'anomalies':i} for i,(r,t) in enumerate(expected)]
        def query(sql,moteur=None,**params):
            with engine.connect() as cx: return pd.read_sql(text(sql),cx,params=params)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'reports').mkdir();suites=root/'reports/suites';suites.mkdir()
            scope={'pd':pd,'json':json,'os':os,'Path':Path,'ROOT':root,'SUITES':suites,'SCHEMA':'source_fixture',
                   'BATCH':'L1','HISTORY_SCHEMA':'history_fixture','TABLE_CLIENT':'clients','TABLE_CONTRAT':'contracts',
                   'WRITER':engine,'text':text,'resultats':results,'display':lambda value:None,'query':query}
            with patch.dict(os.environ,{'DQ_S2_EXECUTION_REPORT':str(root/'reports/S2_execution.json')}):
                exec(compile(''.join(notebook('S2_US10_regles_en_tests')['cells'][15]['source']),'<us10-history>','exec'),scope)
                recorded=json.loads((root/'reports/S2_execution.json').read_text())
                self.assertEqual(recorded['history_ids'],list(range(1,9)))
                # Une exécution ultérieure partielle ne doit remplacer aucun contrôle sélectionné.
                with engine.begin() as cx:
                    cx.exec_driver_sql("INSERT INTO history_fixture.dq_history(batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs) VALUES('L1','BRONZE','RQ-001','contracts',100,99)")
                cell=''.join(notebook('S2_g02')['cells'][34]['source'])
                exec(compile(cell,'<us15-history>','exec'),scope)
                selected=scope['historique_us15']
                self.assertEqual(set(selected.id),set(range(1,9)))
                self.assertEqual(selected.loc[selected.rule_id.eq('RQ-001'),'nb_echecs'].tolist(),[0])
                recorded['schema']='other_source'
                (root/'reports/S2_execution.json').write_text(json.dumps(recorded))
                with self.assertRaisesRegex(ValueError,'ne correspond pas'):
                    exec(compile(cell,'<us15-wrong-scope>','exec'),scope)

    def test_history_same_timestamp_normalizes_scope_and_uses_id(self):
        measures=[{'id':1,'couche':'GOLD','rule_id':'RQ-019','table_cible':'S4R19_client_unique','nb_testees':10,'nb_echecs':1,'mesure_le':'2026-01-01'},
                  {'id':2,'couche':'GOLD','rule_id':'RQ-019','table_cible':'S5_client_unique','nb_testees':10,'nb_echecs':0,'mesure_le':'2026-01-01'}]
        with patch.object(s5,'rows',return_value=measures):
            history=s5._history(None,'L1',s5.Layout())
        self.assertEqual(history['mesures_courantes'],1)
        self.assertEqual(history['mesures'][0]['id'],2)


if __name__ == '__main__':
    unittest.main()
