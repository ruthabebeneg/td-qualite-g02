"""Épreuves RQ-019 sur données synthétiques et schémas exclusivement isolés.

Aucune fonction ne s'exécute à l'import ; run_tests est appelé du notebook S4.
Les fixtures n'ont aucune valeur de validation humaine.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from uuid import uuid4

from sqlalchemy import text
import s4_rq019 as rq
import s5_engineering as s5

BATCH = 'L-2026-10-01'


def _record(number, *, source='crm', name='DUPONT', given='JEAN', born=date(1980, 1, 1),
            town='PARIS', country='FR', kind='PP', email=None):
    return dict(silver_row_id=number, bronze_row_id=number, source_systeme=source,
                source_id=f'SRC{number:03d}', nature_personne=kind,
                type_personne='souscripteur', identite_normalisee=name,
                prenom_normalise=given, date_naissance=born, pays_iso=country,
                ville_normalisee=town, cp='01500', adresse_normalisee='1 RUE TEST',
                telephone_normalise='0612345678', email_normalise=email,
                statut_qualite='VALIDE', _batch_id=BATCH)


def _inputs(records):
    xrefs = [dict(cli_id=f'CLI-{i:06d}', source_systeme=r['source_systeme'],
                  source_id=r['source_id'], silver_row_id=r['silver_row_id'],
                  bronze_row_id=r['bronze_row_id']) for i,r in enumerate(records,1)]
    gold = [dict(cli_id=x['cli_id'], nom_reference=r['identite_normalisee'],
                 date_naissance=r['date_naissance'], cp=r['cp'],
                 ville=r['ville_normalisee'], pays_iso=r['pays_iso'],
                 telephone=r['telephone_normalise'], email=r['email_normalise'],
                 nb_identifiants_source=1, statut_client='ACTIF', _batch_id=BATCH,
                 nature_personne=r['nature_personne'], motif_revue=None)
            for r,x in zip(records,xrefs)]
    return records,xrefs,gold


def _label(a,b,value):
    return dict(gauche_systeme=a['source_systeme'],gauche_id=a['source_id'],
                droite_systeme=b['source_systeme'],droite_id=b['source_id'],
                meme_personne=value)


def _synthetic_inputs():
    records=[_record(1),_record(2,source='cif'),
             _record(3,name='MARTIN',born=date(1970,1,1),email='partage@example.fr'),
             _record(4,name='MARTIN',born=date(1990,1,1),email='partage@example.fr'),
             _record(5,name='MEUNIER',given='ALICE',born=date(1985,1,1),email='unique@example.fr')]
    # L'identifiant bronze est local : les deux origines peuvent porter la même valeur.
    records[1]['bronze_row_id']=1
    return _inputs(records)


def _schema(cx,schema):
    assert schema.startswith('s5_test_rq019_'),schema
    cx.execute(text(f'CREATE DATABASE {s5.ident(schema)} CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin'))


def _insert(cx,schema,name,data):
    if not data:return
    fields=list(data[0]); cols=','.join(s5.ident(x) for x in fields)
    binds=','.join(':'+x for x in fields)
    cx.execute(text(f'INSERT INTO {s5.table(schema,name)} ({cols}) VALUES ({binds})'),data)


def _prepare(engine,prefix):
    gold,dq,silver=prefix+'_gold',prefix+'_dq',prefix+'_silver'
    records,xrefs,clients=_synthetic_inputs()
    contracts=[]
    for num,sub,insured in [(1,'CLI-000001','CLI-000002'),(2,'CLI-000003',None),
                            (3,'CLI-000005','CLI-000004'),(4,'CLI-000005',None)]:
        contracts.append(dict(contrat_id=f'CT{num:03d}',cli_souscripteur=sub,cli_assure=insured,
            code_type='TEST',date_debut=date(2026,1,1),date_fin=date(2027,1,1),
            duree_garantie_mois=12,prime_annuelle=100,date_derniere_cotisation=date(2026,10,1),
            silver_row_id=num,bronze_row_id=num,_batch_id=BATCH))
    claims=[dict(sinistre_id=f'SIN{i:03d}',contrat_id=f'CT{i:03d}',
             date_survenance=date(2026,8,1),montant_estime=1,
             adresse_sinistre='1 RUE TEST',cp_sinistre='01500',id_ban='BAN-TEST',
             silver_row_id=i,bronze_row_id=i,_batch_id=BATCH) for i in range(1,5)]
    with engine.begin() as cx:
        for schema in [gold,dq,silver]:_schema(cx,schema)
        for table in ['client_unique','xref_identifiants','contrat_certifie','sinistre_certifie']:
            cx.execute(text(f'CREATE TABLE {s5.table(gold,table)} LIKE {s5.table("gold",table)}'))
        for table in ['regle','dq_history','rejets','s4_manifeste']:
            cx.execute(text(f'CREATE TABLE {s5.table(dq,table)} LIKE {s5.table("dq",table)}'))
        cx.execute(text(f'INSERT INTO {s5.table(dq,"regle")} SELECT * FROM dq.regle'))
        for table in ['client','contrat','sinistre']:
            cx.execute(text(f'CREATE TABLE {s5.table(silver,table)} LIKE {s5.table("silver",table)}'))
        _insert(cx,gold,'client_unique',clients);_insert(cx,gold,'xref_identifiants',xrefs)
        _insert(cx,gold,'contrat_certifie',contracts);_insert(cx,gold,'sinistre_certifie',claims)
        _insert(cx,silver,'client',records)
        _insert(cx,dq,'s4_manifeste',[dict(batch_id=BATCH,configuration_sha256='a'*64,
                                        etat='TEST_NON_ACCEPTE',accepte=0)])
    return dict(gold=gold,dq=dq,silver=silver), (records,xrefs,clients)


def _apply(engine,plan,schemas,**kwargs):
    return rq.apply(engine,plan,batch=BATCH,gold=schemas['gold'],dq=schemas['dq'],**kwargs)


def _snapshot(engine,schemas):
    with engine.connect() as cx:
        result={}
        for schema in schemas.values():
            for table in cx.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema=:s AND table_type='BASE TABLE' ORDER BY table_name"),{'s':schema}).scalars():
                # L'état du traitement contient dates techniques ; leur stabilité
                # est volontairement contrôlée aussi lors d'une panne transactionnelle.
                result[schema+'.'+table]=s5.fingerprint_table(cx,schema,table)
        return result


def run_tests(engine):
    results=[]
    owned=[]
    def record(name,fn):
        value=fn() or {}
        results.append(dict(cas=name,etat='PASSE',**value))

    def compatible():
        a,b=_record(1),_record(2,source='cif')
        assert rq.compatible_records(a,b)
        plan=rq.build_plan(*_inputs([a,b]),[])
        assert len(set(plan['mapping'].values()))==1 and not plan['excluded_cli']
        assert len(plan['merges'])==1
        return {'sources_preservees':2}
    record('fusion_compatible',compatible)

    for field,value in [('date_naissance',date(1990,1,1)),('nature_personne','PM'),
                        ('pays_iso','BE'),('ville_normalisee','LYON')]:
        def incompatible(field=field,value=value):
            a,b=_record(1),_record(2);b[field]=value
            assert not rq.compatible_records(a,b)
            # Positif pédagogique ne doit jamais écraser un conflit bloquant.
            plan=rq.build_plan(*_inputs([a,b]),[_label(a,b,1)])
            assert len(set(plan['mapping'].values()))==2 and not plan['merges']
            return {'conflit':field,'fusion_refusee':True}
        record('conflit_'+field,incompatible)

    def negative_label():
        a,b=_record(1),_record(2)
        negative={frozenset({(a['source_systeme'],a['source_id']),(b['source_systeme'],b['source_id'])})}
        assert not rq.compatible_records(a,b,negative)
        plan=rq.build_plan(*_inputs([a,b]),[_label(a,b,0)])
        assert not plan['merges']
        return {'label_negatif_prioritaire':True}
    record('label_negatif',negative_label)

    def full_group():
        records,xrefs,gold=_inputs([_record(1),_record(2),_record(3,town='LYON')])
        # Le CLI 2 possède un membre contradictoire non visible sur la paire 1/2.
        xrefs[2]['cli_id']=xrefs[1]['cli_id'];gold=gold[:2]
        plan=rq.build_plan(records,xrefs,gold,[])
        assert not plan['merges'] and len(set(plan['mapping'].values()))==2
        return {'tous_les_membres_verifies':True}
    record('groupe_complet',full_group)

    def no_transitivity():
        a,b,c=_record(1),_record(2),_record(3)
        plan=rq.build_plan(*_inputs([a,b,c]),[_label(a,b,1),_label(b,c,1),_label(a,c,0)])
        assert plan['mapping']['CLI-000001']!=plan['mapping']['CLI-000003']
        assert set(plan['excluded_cli'])=={'CLI-000001','CLI-000002','CLI-000003'}
        return {'positifs_non_etendus_par_transitivite':True,'cli_en_revue':3}
    record('transitivite_non_prouvee',no_transitivity)

    def unknown():
        a,b=_record(1,kind='INCONNUE'),_record(2,kind='INCONNUE')
        assert not rq.compatible_records(a,b)
        plan=rq.build_plan(*_inputs([a,b]),[])
        assert not plan['merges']
        return {'nature_inconnue_non_fusionnee':True}
    record('nature_inconnue',unknown)

    def overlap():
        inputs=_synthetic_inputs();plan=rq.build_plan(*inputs,[])
        assert set(plan['excluded_cli'])=={'CLI-000003','CLI-000004'}
        assert len(plan['excluded_cli'])==len(set(plan['excluded_cli']))
        assert plan['mapping']['CLI-000001']==plan['mapping']['CLI-000002']
        return {'cli_exclus_distincts':2,'fusion_admise':1}
    record('signatures_chevauchantes',overlap)

    def order_stable():
        inputs=_synthetic_inputs();p=rq.build_plan(*inputs,[])
        rev=[list(reversed(x)) for x in inputs];q=rq.build_plan(*rev,[])
        for key in ['mapping','excluded_cli','merges']:
            assert p[key]==q[key],key
        return {'ordre_entree_sans_effet':True}
    record('determinisme_plan',order_stable)

    def db_case(name,fn):
        prefix='s5_test_rq019_'+uuid4().hex[:12]
        schemas={name:prefix+'_'+name for name in ('gold','dq','silver')}
        owned.extend(schemas.values())
        try:
            schemas,inputs=_prepare(engine,prefix)
            with engine.begin() as cx:rq.prepare(cx,schemas['gold'],schemas['dq'])
            record(name,lambda:fn(schemas,inputs))
        finally:
            with engine.begin() as cx:
                for schema in reversed(list(schemas.values())):
                    assert schema.startswith('s5_test_rq019_')
                    cx.execute(text(f'DROP DATABASE IF EXISTS {s5.ident(schema)}'))

    def success(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);_apply(engine,plan,schemas)
        with engine.connect() as cx:
            clients=s5.rows(cx,f'SELECT cli_id,cp,nb_identifiants_source FROM {s5.table(schemas["gold"],"client_unique")} ORDER BY cli_id')
            assert [x['cli_id'] for x in clients]==['CLI-000001','CLI-000005']
            assert clients[0]['nb_identifiants_source']==2 and clients[0]['cp']=='01500'
            x=s5.rows(cx,f'SELECT * FROM {s5.table(schemas["gold"],"xref_identifiants")}')
            assert len(x)==3 and len({(r['source_systeme'],r['source_id']) for r in x})==3
            assert len({(r['source_systeme'],r['bronze_row_id']) for r in x})==3
            contracts=s5.rows(cx,f'SELECT * FROM {s5.table(schemas["gold"],"contrat_certifie")} ORDER BY contrat_id')
            assert [r['contrat_id'] for r in contracts]==['CT001','CT004']
            assert contracts[0]['cli_souscripteur']==contracts[0]['cli_assure']=='CLI-000001'
            claims=s5.rows(cx,f'SELECT sinistre_id FROM {s5.table(schemas["gold"],"sinistre_certifie")} ORDER BY sinistre_id')
            assert [r['sinistre_id'] for r in claims]==['SIN001','SIN004']
            reject=s5.rows(cx,f'SELECT * FROM {s5.table(schemas["dq"],"rejets")}')
            keys={(r['entite'],r['source_systeme'],r['bronze_row_id']) for r in reject}
            assert len(keys)==6 and len(reject)==6
            assert cx.execute(text(f'SELECT accepte FROM {s5.table(schemas["dq"],"s4_manifeste")}')).scalar_one()==0
            assert cx.execute(text(f'SELECT COUNT(*) FROM {s5.table(schemas["silver"],"client")}')).scalar_one()==5
        return {'clients_retenus':2,'xref_retenus':3,'contrats_retenus':2,'sinistres_retenus':2,
                'lignes_rejetees_distinctes':6,'sources_qualifiees':True,'owner_non_accepte':True}
    db_case('application_conservation_dependances',success)

    def replay(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);_apply(engine,plan,schemas)
        before=_snapshot(engine,schemas)
        _apply(engine,plan,schemas)
        assert _snapshot(engine,schemas)==before
        return {'empreintes_identiques':True,'rejets_sans_doublon':True}
    db_case('rejeu_idempotent',replay)

    for phase in ['after_delete','after_insert']:
        def rollback(schemas,inputs,phase=phase):
            plan=rq.build_plan(*inputs,[])
            # La DDL additive est préparée avant le snapshot ; la première
            # application doit annuler aussi les lignes de référence et d'état.
            before=_snapshot(engine,schemas)
            try:_apply(engine,plan,schemas,fail_at=phase)
            except Exception as exc:
                assert 'SIMUL' in str(exc).upper() or 'PANNE' in str(exc).upper() or phase in str(exc),str(exc)
            else:raise AssertionError('La panne injectée doit se produire')
            assert _snapshot(engine,schemas)==before
            return {'phase':phase,'rollback_integral':True}
        db_case('rollback_'+phase,rollback)

    def changed_gold(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);_apply(engine,plan,schemas)
        with engine.begin() as cx:
            cx.execute(text(f"UPDATE {s5.table(schemas['gold'],'client_unique')} SET nom_reference='MODIFICATION EXTERIEURE' WHERE cli_id='CLI-000005'"))
        before=_snapshot(engine,schemas)
        try:_apply(engine,plan,schemas)
        except Exception as exc:
            assert any(x in str(exc).upper() for x in ['MODIFI','DIFFER','INATTEND','DIVERG','CHANG']),str(exc)
        else:raise AssertionError('Un gold modifié hors traitement doit être refusé')
        assert _snapshot(engine,schemas)==before
        return {'mutation_inattendue_refusee':True}
    db_case('gold_inattendu_refuse',changed_gold)

    def restore(schemas,inputs):
        plan=rq.build_plan(*inputs,[])
        with engine.connect() as cx:before=rq.fingerprints(cx,schemas['gold'],schemas['dq'])
        _apply(engine,plan,schemas)
        restored=_apply(engine,plan,schemas,restore=True)
        assert restored['etat']=='REFERENCE'
        with engine.connect() as cx:
            assert rq.fingerprints(cx,schemas['gold'],schemas['dq'])==before
        _apply(engine,plan,schemas)
        with engine.connect() as cx:
            assert cx.execute(text(f"SELECT COUNT(*) FROM {s5.table(schemas['gold'],'client_unique')}")).scalar_one()==2
        return {'reference_restituee_exactement':True,'reapplication_possible':True}
    db_case('restauration_reference',restore)

    def altered_reference(schemas,inputs):
        plan=rq.build_plan(*inputs,[])
        _apply(engine,plan,schemas)
        with engine.begin() as cx:
            cx.execute(text(f"UPDATE {s5.table(schemas['dq'],'rq019_reference_sinistre_certifie')} SET adresse_sinistre='REFERENCE ALTEREE'"))
        before=_snapshot(engine,schemas)
        try:_apply(engine,plan,schemas,restore=True)
        except ValueError as exc:assert 'référence' in str(exc).lower() and 'altérée' in str(exc).lower()
        else:raise AssertionError('Une sauvegarde altérée ne doit pas être restaurée')
        assert _snapshot(engine,schemas)==before
        return {'reference_alteree_refusee_avant_ecriture':True}
    db_case('reference_alteree_refusee',altered_reference)

    def auditor(schemas):
        def audit(cx):
            actual=rq.signature_summary(rq._read(cx,schemas['silver'],'client'),
                rq._read(cx,schemas['gold'],'xref_identifiants'),rq._read(cx,schemas['gold'],'client_unique'))
            return actual,[]
        return audit

    def restored_history(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);audit=auditor(schemas)
        _apply(engine,plan,schemas,_test_auditor=audit)
        with engine.connect() as cx:
            assert all(m['nb_echecs']==0 for m in audit(cx)[0])
        _apply(engine,plan,schemas,restore=True,_test_auditor=audit)
        with engine.connect() as cx:
            rows=s5.rows(cx,f"SELECT rule_id,table_cible,nb_testees,nb_echecs FROM {s5.table(schemas['dq'],'dq_history')} ORDER BY id")
            assert len(rows)==8 and sum(r['nb_echecs'] for r in rows[-4:])>0
            class Layout:
                dq=schemas['dq']
            latest=s5._history(cx,BATCH,Layout())['mesures']
            assert len(latest)==4 and sum(r['nb_echecs'] for r in latest)>0
        return {'huit_mesures_conservees':True,'mesures_courantes_reference_restauree':True}
    db_case('historique_apres_restauration',restored_history)

    def late_rollback(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);before=_snapshot(engine,schemas)
        try:_apply(engine,plan,schemas,fail_at='after_audit',_test_auditor=auditor(schemas))
        except RuntimeError as exc:assert 'after_audit' in str(exc)
        else:raise AssertionError('La panne tardive devait se produire')
        assert _snapshot(engine,schemas)==before
        return {'rollback_gold_rejets_manifeste_etat_references_historique':True}
    db_case('rollback_apres_historisation',late_rollback)

    def altered_plan(schemas,inputs):
        plan=rq.build_plan(*inputs,[])
        before=_snapshot(engine,schemas)
        plan['mapping']['CLI-000005']='CLI-000001'
        try:_apply(engine,plan,schemas)
        except ValueError as exc:assert 'altéré' in str(exc)
        else:raise AssertionError('Un plan altéré doit être refusé')
        assert _snapshot(engine,schemas)==before
        return {'plan_altere_refuse_avant_ecriture':True}
    db_case('plan_altere',altered_plan)

    def changed_plan(schemas,inputs):
        plan=rq.build_plan(*inputs,[]);_apply(engine,plan,schemas)
        before=_snapshot(engine,schemas)
        different=deepcopy(plan);different['note_synthetique']='autre plan'
        different['sha256']=s5.digest({k:v for k,v in different.items() if k!='sha256'})
        try:_apply(engine,different,schemas)
        except ValueError as exc:assert 'Plan différent' in str(exc)
        else:raise AssertionError('Un plan différent doit être refusé sur la référence existante')
        assert _snapshot(engine,schemas)==before
        return {'changement_plan_refuse':True}
    db_case('plan_different_reference',changed_plan)

    with engine.connect() as cx:
        assert all(not cx.execute(text('SELECT 1 FROM information_schema.schemata WHERE schema_name=:s'),{'s':name}).first() for name in owned)
    return {'synthetique':True,'nombre_tests':len(results),'tous_passes':True,
            'schemas_nettoyes':True,'limite':'Aucune décision humaine ni donnée nominale modifiée.',
            'tests':results}
