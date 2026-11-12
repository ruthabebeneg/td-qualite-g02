"""Épreuves S5 MariaDB, exclusivement sur des fixtures synthétiques isolées.

run_tests ne modifie jamais les sources, bronze, silver, gold ou dq nominaux.
Les GO et identités de fixtures ne sont pas des validations humaines.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from contextvars import ContextVar
from uuid import uuid4
from unittest.mock import patch
from pathlib import Path
import s5_mesures
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
import s5_engineering as s5

BATCH = 'TEST-S5-SYNTHETIQUE'
_TEST_LAYOUT=ContextVar("s5_test_layout")


def _layout():
    return _TEST_LAYOUT.get()



def _reset(engine):
    """Les noms sont constants et contrôlés ; aucun nom nominal n'est accepté."""
    schemas = (_layout().target, _layout().gold, _layout().dq)
    assert all(s.startswith('s5_test_') for s in schemas)
    with engine.begin() as c:
        for schema in schemas:
            c.execute(text(f'DROP DATABASE IF EXISTS {s5.ident(schema)}'))
            c.execute(text(f'CREATE DATABASE {s5.ident(schema)} CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin'))
        for name in ['regle', 'dq_history', 'certificat_qualite', 's4_manifeste']:
            c.execute(text(f'CREATE TABLE {s5.table(_layout().dq,name)} LIKE {s5.table("dq",name)}'))
        for source, _ in s5.MAPPING:
            c.execute(text(f'CREATE TABLE {s5.table(_layout().gold,source)} LIKE {s5.table("gold",source)}'))
        c.execute(text(f'''INSERT INTO {s5.table(_layout().dq,'regle')}
            (rule_id,libelle,dimension,porte,severite,seuil_min)
            VALUES('RQ-001','TEST SYNTHETIQUE dates','Cohérence','S','BLOQUANTE',100),('RQ-025','TEST reconciliation','Intégrité','C','BLOQUANTE',100)'''))
        c.execute(text(f'''INSERT INTO {s5.table(_layout().dq,'dq_history')}
            (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
            VALUES(:b,'SILVER','RQ-001','contrat',1,0)'''), {'b': BATCH})
        c.execute(text(f'''INSERT INTO {s5.table(_layout().dq,'s4_manifeste')}
            (batch_id,configuration_sha256,etat,accepte)
            VALUES(:b,:h,'TEST_SYNTHETIQUE_ACCEPTE',1)'''), {'b': BATCH, 'h': '1'*64})
        c.execute(text(f'''INSERT INTO {s5.table(_layout().gold,'client_unique')}
            (cli_id,nom_reference,nb_identifiants_source,statut_client,_batch_id,cp,telephone,email)
            VALUES('CLI-TEST01','TEST SYNTHETIQUE',1,'ACTIF',:b,'01500',NULL,'')'''), {'b': BATCH})
        c.execute(text(f'''INSERT INTO {s5.table(_layout().gold,'contrat_certifie')}
            (contrat_id,cli_souscripteur,cli_assure,code_type,date_debut,date_fin,
             duree_garantie_mois,prime_annuelle,date_derniere_cotisation,silver_row_id,bronze_row_id,_batch_id)
            VALUES('CT-TEST01','CLI-TEST01',NULL,'TEST','2026-01-01','2027-01-01',12,123.45,'2026-10-01',1,1,:b)'''), {'b': BATCH})
        c.execute(text(f'''INSERT INTO {s5.table(_layout().gold,'sinistre_certifie')}
            (sinistre_id,contrat_id,date_survenance,montant_estime,adresse_sinistre,
             cp_sinistre,silver_row_id,bronze_row_id,_batch_id)
            VALUES('SIN-TEST01','CT-TEST01','2026-08-01',0.01,' ', '01500',1,1,:b)'''), {'b': BATCH})
    s5.init_storage(engine, _layout())
    s5.prepare_target(engine, _layout())


def _owner(engine):
    history = s5.audit_history(engine, BATCH, _layout())
    with engine.connect() as c:
        gold = s5.fingerprint_gold(c, BATCH, _layout())
        conf = c.execute(text(f'SELECT configuration_sha256 FROM {s5.table(_layout().dq,"s4_manifeste")} WHERE batch_id=:b'), {'b': BATCH}).scalar_one()
    return {'decision': 'ACCEPTE', 'batch_id': BATCH, 'configuration_sha256': conf,
            'empreinte_gold': gold['sha256'], 'historique_sha256': history['sha256'],
            'decideur': 'FIXTURE_TEST_SYNTHETIQUE_SANS_VALIDATION_HUMAINE',
            'date_decision': '2026-11-08', 'signature': 'FIXTURE_TECHNIQUE_NON_HUMAINE',
            'justification': 'Test isolé du mécanisme ; aucune approbation du lot réel.'}


def _go(engine):
    cert = s5.certify(engine,BATCH,_owner(engine),_layout(),measurement_attestation=s5.measure_fixture(engine,BATCH,_layout()))
    assert cert['decision'] == 'GO', cert.get('motifs')
    assert cert['synthetique'] is True
    return cert


def _target(engine):
    with engine.connect() as c:
        return {name: s5.fingerprint_table(c, _layout().target, name)
                for _, name in s5.MAPPING}


def _logs(engine):
    with engine.connect() as c:
        return (c.execute(text(f"SELECT COUNT(*) FROM {s5.table(_layout().dq,'s5_publication')}" )).scalar_one(),
                c.execute(text(f"SELECT COUNT(*) FROM {s5.table(_layout().dq,'dq_history')} WHERE couche='CRM'" )).scalar_one())


def _refuse(engine, certificat_id, code):
    before = _target(engine)
    audit_before = _logs(engine)
    try:
        s5.publish(engine, BATCH, certificat_id, _layout())
    except s5.PublicationRefusee as exc:
        message = str(exc)
        assert code in message, (code, message)
    else:
        raise AssertionError(f'Publication acceptée à tort : {code}')
    assert _target(engine) == before, 'Cible modifiée malgré le refus'
    assert _logs(engine)==audit_before, 'Journal/RQ025 modifiés malgré le refus'
    return {'message': message, 'cible_inchangee': True, 'chargement': False}


def run_tests(engine):
    """Exécute réellement les cas et lève si un test échoue ; nettoie ses schémas."""
    prefix='s5_test_engineer_'+uuid4().hex[:12]
    token=_TEST_LAYOUT.set(s5.Layout(prefix+'_gold',prefix+'_dq',prefix+'_target'))
    owned_schemas=[_layout().target,_layout().gold,_layout().dq,prefix+'_silver',prefix+'_bronze']
    results = []

    def run(name, fn):
        _reset(engine)
        evidence = fn() or {}
        results.append({'cas': name, 'etat': 'PASSE', **evidence})

    def missing():
        return _refuse(engine, 'CERTIFICAT_INEXISTANT', 'CERTIFICAT_ABSENT')

    def no_go():
        cert = s5.certify(engine, BATCH, None, _layout())
        assert cert['decision'] == 'NO_GO' and cert['owner'] is None
        return _refuse(engine, cert['certificat_id'], 'CERTIFICAT_NO_GO')

    def changed_gold():
        cert = _go(engine)
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,'client_unique')} SET telephone='0123456789'"))
        return _refuse(engine, cert['certificat_id'], 'EMPREINTE_GOLD_DIFFERENTE')

    def success():
        cert = _go(engine)
        report = s5.publish(engine, BATCH, cert['certificat_id'], _layout())
        assert len(report['reconciliation']) == 3
        for item in report['reconciliation']:
            assert item['gold'] == item['cible'] and item['gold']['lignes'] == 1
        assert all(x['lignes'] == 1 for x in _target(engine).values())
        assert _logs(engine)==(1,3)
        return {'message': report['publication'], 'chargement': True,
                'reconciliation':report['reconciliation'],'journal_publications':1,'mesures_rq025_crm':3}

    def rollback():
        cert = _go(engine)
        s5.publish(engine, BATCH, cert['certificat_id'], _layout())
        # Préexistence réelle de trois tables non vides, dont une valeur différente.
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().target,'client')} SET nom_reference='CIBLE AVANT PANNE'"))
        before = _target(engine)
        logs_before=_logs(engine)
        try:
            s5.publish(engine, BATCH, cert['certificat_id'], _layout(), fail_after=2)
        except s5.PublicationRefusee as exc:
            assert 'PANNE_SIMULEE' in str(exc)
            msg = str(exc)
        else:
            raise AssertionError('La panne injectée ne s’est pas produite')
        assert before == _target(engine) and logs_before==_logs(engine)
        return {'message': msg, 'cible_preexistante_inchangee': True,
                'rollback_integral': True}

    def replay():
        cert = _go(engine)
        s5.publish(engine, BATCH, cert['certificat_id'], _layout())
        before = _target(engine)
        s5.publish(engine, BATCH, cert['certificat_id'], _layout())
        assert before == _target(engine) and _logs(engine)==(2,6)
        return {'journal_publications':2,'mesures_rq025_crm':6,'sans_doublon': True, 'empreintes_identiques': True}

    def changed_catalogue():
        cert = _go(engine)
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'regle')} SET seuil_min=99 WHERE rule_id='RQ-001'"))
        return _refuse(engine, cert['certificat_id'], 'MESURES_OU_CATALOGUE_MODIFIES')

    def changed_history():
        cert = _go(engine)
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'dq_history')} SET nb_echecs=1"))
        return _refuse(engine, cert['certificat_id'], 'MESURES_OU_CATALOGUE_MODIFIES')

    def changed_config():
        cert = _go(engine)
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'s4_manifeste')} SET configuration_sha256=:h"), {'h': '2'*64})
        return _refuse(engine, cert['certificat_id'], 'VALIDATION_OWNER_PERIMEE')

    def missing_measure():
        with engine.begin() as c:
            c.execute(text(f"DELETE FROM {s5.table(_layout().dq,'dq_history')}"))
        cert = s5.certify(engine, BATCH, _owner(engine), _layout())
        assert cert['decision'] == 'NO_GO'
        assert any(x['etat'] == 'NON_MESUREE' for x in cert['couverture'])
        return {'decision': cert['decision'], 'absence_bloquante_detectee': True}

    def empty_population():
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'dq_history')} SET nb_testees=0,nb_echecs=0"))
        cert = s5.certify(engine, BATCH, _owner(engine), _layout())
        assert cert['decision'] == 'NO_GO'
        assert any(x['etat'] == 'POPULATION_ABSENTE' for x in cert['couverture'])
        return {'decision': 'NO_GO', 'population_vide_non_conforme': True}

    def failed_rule():
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,'contrat_certifie')} SET date_fin=date_debut"))
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'dq_history')} SET nb_echecs=1"))
        attestation = s5.measure_fixture(engine, BATCH, _layout())
        cert = s5.certify(engine, BATCH, _owner(engine), _layout(), measurement_attestation=attestation)
        assert cert['decision'] == 'NO_GO'
        assert any(x['etat'] == 'ECHEC' for x in cert['couverture'])
        assert cert['motifs'] == ['COUVERTURE_OU_CONFORMITE_BLOQUANTE_INSUFFISANTE']
        return {'decision': 'NO_GO', 'lot_degrade': True,
                'degradation': 'date_fin = date_debut du contrat synthetique',
                'nb_testees': 1, 'nb_echecs': 1, 'seul_blocage': 'RQ-001'}

    def invalid_measure():
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().dq,'dq_history')} SET nb_echecs=2"))
        cert = s5.certify(engine, BATCH, _owner(engine), _layout())
        assert cert['decision'] == 'NO_GO' and cert['motifs']
        return {'decision': 'NO_GO', 'mesure_invalide_detectee': True}

    def table_empty():
        with engine.begin() as c:
            c.execute(text(f"DELETE FROM {s5.table(_layout().gold,'sinistre_certifie')}"))
        cert = s5.certify(engine, BATCH, _owner(engine), _layout())
        assert cert['decision'] == 'NO_GO' and 'TABLE_GOLD_VIDE' in cert['motifs']
        return {'decision': 'NO_GO'}

    def types():
        values = [None, '', ' ', '01500', '1500', Decimal('0.01'), date(2026, 10, 1)]
        assert len({s5.digest(s5.canonical(v)) for v in values}) == len(values)
        with engine.connect() as c:
            first = s5.fingerprint_gold(c, BATCH, _layout())
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,'client_unique')} SET telephone=''"))
        with engine.connect() as c:
            second = s5.fingerprint_gold(c, BATCH, _layout())
        assert first['sha256'] != second['sha256']
        return {'null_vide_blanc_et_cp_distincts': True, 'decimal_exact': True}

    def concurrent_snapshot():
        cert = _go(engine)
        original = s5.fingerprint_gold
        fired = []
        def overlapping(cx, batch, layout=s5.Layout()):
            proof = original(cx, batch, layout)
            if not fired:
                fired.append(True)
                # Deuxième connexion indépendante qui ignore le verrou nommé.
                with engine.begin() as writer:
                    writer.execute(text(f"UPDATE {s5.table(_layout().gold,'client_unique')} SET nom_reference='MODIFICATION CONCURRENTE'"))
            return proof
        s5.fingerprint_gold = overlapping
        try:
            report = s5.publish(engine, BATCH, cert['certificat_id'], _layout())
        finally:
            s5.fingerprint_gold = original
        assert fired and all(x['gold'] == x['cible'] for x in report['reconciliation'])
        with engine.connect() as c:
            now = original(c, BATCH, _layout())
        assert now['sha256'] != cert['gold']['sha256']
        return {'snapshot_certifie_publie': True, 'ecrivain_independant_execute': True,
                'reconciliation': report['reconciliation']}

    def lock_refusal():
        cert = _go(engine)
        with engine.connect() as other:
            assert other.execute(text("SELECT GET_LOCK('s4_construction',0)")).scalar_one() == 1
            try:
                return _refuse(engine, cert['certificat_id'], 'CONSTRUCTION_CONCURRENTE')
            finally:
                other.execute(text("SELECT RELEASE_LOCK('s4_construction')"))
                other.commit()

    def no_unsafe_schema():
        try:
            s5.Layout('gold', 'dq', 's5_test_target')
        except ValueError:
            return {'schemas_mixtes_refuses': True}
        raise AssertionError('Mélange nominal/test accepté')

    def immutable_cert():
        cert = s5.certify(engine, BATCH, None, _layout(), certificat_id='TEST_IMMUABLE')
        try:
            s5.certify(engine, BATCH, _owner(engine), _layout(), certificat_id=cert['certificat_id'])
        except ValueError as exc:
            assert 'immuable' in str(exc)
            return {'certificat_immuable': True}
        raise AssertionError('Certificat existant réécrit')

    def non_transactional(target=False):
        cert=_go(engine)
        schema=_layout().target if target else _layout().gold
        name='client' if target else 'client_unique'
        with engine.begin() as c:
            c.execute(text(f"ALTER TABLE {s5.table(schema,name)} ENGINE=MyISAM"))
        with engine.connect() as c:
            count=c.execute(text(f"SELECT COUNT(*) FROM {s5.table(_layout().dq,'certificat_qualite')}" )).scalar_one()
        try:
            s5.certify(engine,BATCH,_owner(engine),_layout())
        except s5.PublicationRefusee as exc:
            assert 'MOTEUR_NON_TRANSACTIONNEL' in str(exc)
        else:
            raise AssertionError('Certification MyISAM acceptée')
        with engine.connect() as c:
            assert c.execute(text(f"SELECT COUNT(*) FROM {s5.table(_layout().dq,'certificat_qualite')}" )).scalar_one()==count
        return {'certification_refusee_avant_ecriture':True,**_refuse(engine,cert['certificat_id'],'MOTEUR_NON_TRANSACTIONNEL')}

    def changed_policy():
        cert=_go(engine)
        original=Path.read_bytes
        def changed(path):
            value=original(path)
            return value+b'\n-- ALTERATION TEST SYNTHETIQUE\n' if path.name=='S5_decision.sql' else value
        with patch.object(Path,'read_bytes',changed):
            result=_refuse(engine,cert['certificat_id'],'POLITIQUE_CERTIFICATION_MODIFIEE')
        return {'octets_sql_modifies_a_la_lecture':True,**result}

    def changed_scopes():
        cert=_go(engine)
        original=s5.required_scopes
        def changed(catalogue,**kwargs):
            return original(catalogue,**kwargs)+[{'rule_id':'RQ-001','couche':'GOLD','table_logique':'nouveau_scope','seuil_min':'100.00'}]
        with patch.object(s5,'required_scopes',changed):
            return _refuse(engine,cert['certificat_id'],'POLITIQUE_CERTIFICATION_MODIFIEE')

    def absent_gold_lineage():
        with engine.begin() as c:
            c.execute(text(f"INSERT INTO {s5.table(_layout().dq,'regle')} (rule_id,libelle,dimension,porte,severite,seuil_min) VALUES('RQ-023','TEST lineage','Traçabilité','S','BLOQUANTE',100)"))
            for name in ('client_crm','client_cif','contrat_crm','sinistre_crm'):
                c.execute(text(f"INSERT INTO {s5.table(_layout().dq,'dq_history')} (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs) VALUES(:b,'SILVER','RQ-023',:t,1,0)"),{'b':BATCH,'t':name})
        cert=s5.certify(engine,BATCH,_owner(engine),_layout())
        missing=[m for m in cert['couverture'] if m['rule_id']=='RQ-023' and m['couche']=='GOLD' and m['etat']=='NON_MESUREE']
        assert len(missing)==6 and cert['decision']=='NO_GO'
        return {'decision':'NO_GO','perimetres_gold_manquants':len(missing)}

    def failed_gold_extra():
        with engine.begin() as c:
            c.execute(text(f"INSERT INTO {s5.table(_layout().dq,'dq_history')} (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs) VALUES(:b,'GOLD','RQ-001','contrat',1,1)"),{'b':BATCH})
        cert=s5.certify(engine,BATCH,_owner(engine),_layout())
        assert cert['decision']=='NO_GO' and any(m['couche']=='GOLD' and m['etat']=='ECHEC' for m in cert['couverture'])
        return {'decision':'NO_GO','regression_gold_non_ignoree':True}

    def stale_measurement_attestation():
        attestation=s5.measure_fixture(engine,BATCH,_layout())
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,'client_unique')} SET nom_reference='CONTENU MODIFIE AVANT CERTIFICATION'"))
        cert=s5.certify(engine,BATCH,_owner(engine),_layout(),measurement_attestation=attestation)
        assert cert['decision']=='NO_GO' and 'ATTESTATION_CONTROLES_COMPLETS_ABSENTE_OU_PERIMEE' in cert['motifs']
        return {'decision':'NO_GO','attestation_perimee_detectee':True}

    def missing_measurement_attestation():
        cert=s5.certify(engine,BATCH,_owner(engine),_layout())
        assert cert['decision']=='NO_GO' and 'ATTESTATION_CONTROLES_COMPLETS_ABSENTE_OU_PERIMEE' in cert['motifs']
        assert all(m['conforme'] for m in cert['couverture'])
        return {'decision':'NO_GO','mesures_conformes_sans_preuve_de_provenance_refusees':True}

    def other_batch_target():
        cert=_go(engine)
        s5.publish(engine,BATCH,cert['certificat_id'],_layout())
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().target,'sinistre')} SET _batch_id='AUTRE-LOT-TEST'"))
        return _refuse(engine,cert['certificat_id'],'CIBLE_AUTRE_LOT_NON_CERTIFIE')

    def orphan(column,table_name):
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,table_name)} SET {s5.ident(column)}='ABSENT'"))
        cert=s5.certify(engine,BATCH,_owner(engine),_layout(),measurement_attestation=s5.measure_fixture(engine,BATCH,_layout()))
        assert cert['decision']=='NO_GO' and 'GOLD_ORPHELIN' in cert['motifs']
        assert sum(cert['integrite_gold'].values())==1
        return {'decision':'NO_GO','orphelins_mesures':cert['integrite_gold']}

    def trigger_changes_copy():
        cert=_go(engine)
        s5.publish(engine,BATCH,cert['certificat_id'],_layout())
        with engine.begin() as c:
            c.execute(text(f"CREATE TRIGGER {s5.table(_layout().target,'s5_altere_copie')} BEFORE INSERT ON {s5.table(_layout().target,'contrat')} FOR EACH ROW SET NEW.prime_annuelle=NEW.prime_annuelle+1"))
        return {'rollback_cible_et_journal':True,**_refuse(engine,cert['certificat_id'],'RQ025_ECART_CONTENU')}

    def failed_publication_journal():
        cert=_go(engine)
        s5.publish(engine,BATCH,cert['certificat_id'],_layout())
        before=_target(engine); logs_before=_logs(engine)
        with engine.begin() as c:
            c.execute(text(f"CREATE TRIGGER {s5.table(_layout().dq,'s5_journal_refuse')} BEFORE INSERT ON {s5.table(_layout().dq,'s5_publication')} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PANNE_JOURNAL_SYNTHETIQUE'"))
        try:
            s5.publish(engine,BATCH,cert['certificat_id'],_layout())
        except DBAPIError as exc:
            assert 'PANNE_JOURNAL_SYNTHETIQUE' in str(exc)
        else:
            raise AssertionError('Le journal devait refuser')
        assert before==_target(engine) and logs_before==_logs(engine)
        return {'rollback_trois_tables_et_trois_rq025':True,'journal_inchange':True}

    def missing_links():
        silver=prefix+'_silver'; bronze=prefix+'_bronze'
        with engine.begin() as c:
            for schema in (silver,bronze):
                c.execute(text(f'CREATE DATABASE {s5.ident(schema)} CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin'))
            c.execute(text(f'CREATE TABLE {s5.table(silver,"client")} LIKE silver.client'))
            c.execute(text(f'CREATE TABLE {s5.table(bronze,"crm_client")} LIKE bronze.crm_client'))
            c.execute(text(f'CREATE TABLE {s5.table(_layout().gold,"xref_identifiants")} LIKE gold.xref_identifiants'))
            c.execute(text(f"INSERT INTO {s5.table(silver,'client')} (silver_row_id,bronze_row_id,source_systeme,source_id,_batch_id) VALUES(1,1,'crm','TEST',:b)"),{'b':BATCH})
        query=s5_mesures.lineage_queries(_layout().gold,silver,bronze)['silver_xref_gold']
        with engine.connect() as c:
            no_xref=tuple(map(int,c.execute(text(query),{'b':BATCH}).one()))
        assert no_xref==(1,1)
        with engine.begin() as c:
            c.execute(text(f"INSERT INTO {s5.table(_layout().gold,'xref_identifiants')} VALUES('ABSENT','crm','TEST',1,1)"))
        with engine.connect() as c:
            no_gold=tuple(map(int,c.execute(text(query),{'b':BATCH}).one()))
        assert no_gold==(1,1)
        with engine.begin() as c:
            c.execute(text(f"UPDATE {s5.table(_layout().gold,'xref_identifiants')} SET cli_id='CLI-TEST01'"))
            c.execute(text(f"DELETE FROM {s5.table(silver,'client')}"))
        query=s5_mesures.lineage_queries(_layout().gold,silver,bronze)['xref_crm']
        with engine.connect() as c:
            no_silver=tuple(map(int,c.execute(text(query),{'b':BATCH}).one()))
        assert no_silver==(1,1)
        return {'silver_sans_xref':no_xref,'xref_sans_gold':no_gold,'xref_sans_silver_ou_bronze':no_silver}

    def bounded_pages():
        with engine.begin() as c:
            c.execute(text(f"INSERT INTO {s5.table(_layout().gold,'client_unique')} (cli_id,nom_reference,nb_identifiants_source,statut_client,_batch_id) VALUES('CLI-TEST02','AUTRE TEST',1,'ACTIF',:b)"),{'b':BATCH})
        with engine.connect() as c:
            names=[m['name'] for m in s5.columns(c,_layout().gold,'client_unique')]
            sizes=[len(page) for page in s5.table_pages(c,_layout().gold,'client_unique',names,BATCH,size=1)]
        assert sizes==[1,1]
        return {'tailles_pages':sizes,'lignes_totales':sum(sizes)}

    scenarios = [('sans_certificat', missing), ('certificat_no_go', no_go),
                 ('gold_modifie', changed_gold), ('go_gold_intact', success),
                 ('rollback_apres_contrat', rollback), ('relance_idempotente', replay),
                 ('catalogue_modifie', changed_catalogue), ('historique_modifie', changed_history),
                 ('configuration_modifiee', changed_config), ('mesure_bloquante_absente', missing_measure),
                 ('population_vide', empty_population), ('lot_degrade_no_go', failed_rule),
                 ('mesure_invalide', invalid_measure), ('table_gold_vide', table_empty),
                 ('types_canoniques', types), ('ecriture_concurrente_snapshot', concurrent_snapshot),
                 ('verrou_concurrent', lock_refusal), ('schemas_mixtes', no_unsafe_schema),
                 ('certificat_immuable',immutable_cert),
                 ('myisam_cible',lambda:non_transactional(True)),
                 ('myisam_source',non_transactional),('politique_sql_modifiee',changed_policy),
                 ('scopes_modifies',changed_scopes),('rq023_gold_absente',absent_gold_lineage),
                 ('regression_gold_aval',failed_gold_extra),('attestation_perimee',stale_measurement_attestation),
                 ('attestation_absente',missing_measurement_attestation),('cible_autre_lot',other_batch_target),
                 ('orphelin_souscripteur',lambda:orphan('cli_souscripteur','contrat_certifie')),
                 ('orphelin_assure',lambda:orphan('cli_assure','contrat_certifie')),
                 ('orphelin_sinistre',lambda:orphan('contrat_id','sinistre_certifie')),
                 ('trigger_altere_copie_rollback',trigger_changes_copy),('lineage_absences',missing_links),
                 ('pages_bornees',bounded_pages),('panne_journal_rollback',failed_publication_journal)]
    try:
        for name, fn in scenarios:
            run(name, fn)
    finally:
        with engine.begin() as c:
            for schema in owned_schemas:
                assert schema.startswith('s5_test_')
                c.execute(text(f'DROP DATABASE IF EXISTS {s5.ident(schema)}'))
        with engine.connect() as c:
            remaining=[schema for schema in owned_schemas if c.execute(text("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name=:s"),{'s':schema}).scalar_one()]
        assert remaining==[]
        _TEST_LAYOUT.reset(token)
    return {'synthetique': True, 'lot': BATCH,'schemas_execution':owned_schemas,
            'limite': 'Tests du mécanisme sur fixtures isolées ; aucun GO ni signature du lot réel.',
            'nombre_tests': len(results), 'tous_passes': True, 'schemas_nettoyes': True,
            'tests': results}
