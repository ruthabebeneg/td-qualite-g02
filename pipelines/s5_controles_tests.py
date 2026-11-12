"""Tests purs et MariaDB isolés de l’exécuteur S5.

run_tests ne touche aucune base ; run_db_tests ne modifie que ses fixtures.
"""
from datetime import date
from unittest.mock import patch
import s5_controles as controls


class _Scalar:
    def __init__(self,value):self.value=value
    def scalar_one(self):return self.value


class _Counts:
    def __init__(self,values):self.values=iter(values);self.parameters=[]
    def execute(self,query,parameters):
        self.parameters.append(parameters)
        return _Scalar(next(self.values))


def run_tests():
    results=[]
    def run(name,fn):
        fn();results.append({'cas':name,'etat':'PASSE'})

    def population_empty():
        out={};controls._add(out,'GOLD','RQ-019','test',0,0,'population vide')
        assert out[('GOLD','RQ-019','test')]['taux'] is None
    run('population_vide_sans_100_pourcent',population_empty)

    def invalid_population():
        try:controls._add({},'GOLD','RQ-019','test',1,2,'invalide')
        except ValueError:return
        raise AssertionError('Effectifs impossibles acceptés')
    run('effectifs_impossibles_refuses',invalid_population)

    contracts=[
        {'cli_souscripteur':'A','date_debut':date(2026,10,1),'date_fin':date(2026,10,1),'date_derniere_cotisation':date(2026,7,1)},
        {'cli_souscripteur':'B','date_debut':date(2025,1,1),'date_fin':date(2027,1,1),'date_derniere_cotisation':date(2026,10,1)},
        {'cli_souscripteur':'C','date_debut':date(2025,1,1),'date_fin':date(2027,1,1),'date_derniere_cotisation':None},
        {'cli_souscripteur':'D','date_debut':date(2025,1,1),'date_fin':date(2027,1,1),'date_derniere_cotisation':date(2026,6,30)},
        {'cli_souscripteur':'E','date_debut':date(2026,10,2),'date_fin':date(2027,1,1),'date_derniere_cotisation':date(2026,10,1)}]
    def active_case(counts,view,expected_failures):
        cx=_Counts(counts);out={}
        def data(_cx,sql,params=None):
            return [{'cli_id':i} for i in view] if 'v_client_actif' in sql else contracts
        with patch.object(controls.s5,'rows',data):controls.active_controls(cx,'L-2026-10-01',out)
        m=out[('GOLD','RQ-018','v_client_actif')]
        assert m['nb_testees']==3 and m['nb_echecs']==expected_failures
        assert m['actifs_python']==2
        assert len(cx.parameters)==3 and all(p['reference']==date(2026,10,1) and p['minimum']==date(2026,7,1) for p in cx.parameters)
    run('rq018_bornes_dates_et_cotisation_null',lambda:active_case([2,2,2],['A','B'],0))
    run('rq018_direction_divergente_detectee',lambda:active_case([2,1,2],['A','B'],1))
    run('rq018_meme_compte_identites_differentes_detecte',lambda:active_case([2,2,2],['A','Z'],3))

    def status_failure_is_not_overwritten():
        cx=_Counts([2,2,2])
        def data(_cx,sql,params=None):
            if 'silver.client' in sql:return []
            return [{'cli_id':i} for i in ['A','B']] if 'v_client_actif' in sql else contracts
        bad_status={'rule_id':'RQ-018','table_logique':'v_client_actif','nb_testees':2,'nb_echecs':1,
                    'requete':'CONTROLE_SYNTHETIQUE_STATUT'}
        no_op=lambda *args,**kwargs:None
        with patch.object(controls,'bronze_controls',no_op),patch.object(controls,'client_controls',no_op), \
             patch.object(controls,'silver_controls',no_op),patch.object(controls,'ban_controls',no_op), \
             patch.object(controls,'_keys',no_op),patch.object(controls.s5,'rows',data), \
             patch.object(controls.rq,'checks',lambda *args:([bad_status],[])):
            measured,_=controls.collect(cx,'L-2026-10-01')
        bykey={(m['rule_id'],m['table_logique']):m for m in measured}
        assert bykey[('RQ-018','v_client_actif')]['nb_echecs']==0
        assert bykey[('RQ-018','statut_client_actif')]['nb_echecs']==1
        assert len(bykey)==2
    run('rq018_statut_incorrect_non_ecrase_par_vue_conforme',status_failure_is_not_overwritten)

    ban={'id_ban':'BAN','numero':'12','voie':'rue de l’Église','code_postal':'01500','commune':'Évry'}
    valid={'id_ban':'BAN','adresse_sinistre':'12 RUE DE L EGLISE','cp_sinistre':'01500','ville_sinistre':'EVRY'}
    # L'apostrophe reste significative : le texte nominal concordant est explicite.
    valid['adresse_sinistre']='12 RUE DE L’EGLISE'
    def ban_case(changes,expected):
        row={**valid,**changes};out={}
        def data(_cx,sql,params=None):return [ban] if 'ref_ban' in sql else [row]
        with patch.object(controls.s5,'rows',data),patch.object(controls,'_keys',lambda *args,**kwargs:None):
            controls.ban_controls(object(),'L-2026-10-01',out)
        assert out[('SILVER','RQ-014','sinistre')]['nb_echecs']==expected
        assert out[('GOLD','RQ-014','sinistre')]['nb_echecs']==expected
    run('ban_reference_et_adresse_concordantes',lambda:ban_case({},0))
    run('ban_identifiant_seul_insuffisant_cp',lambda:ban_case({'cp_sinistre':'1500'},1))
    run('ban_identifiant_seul_insuffisant_commune',lambda:ban_case({'ville_sinistre':'AUTRE'},1))
    run('ban_identifiant_seul_insuffisant_adresse',lambda:ban_case({'adresse_sinistre':'99 RUE INCONNUE'},1))
    run('ban_reference_absente_refusee',lambda:ban_case({'id_ban':None},1))
    return {'synthetique':True,'nombre_tests':len(results),'tous_passes':True,
            'ecritures_base':False,'tests':results}


def run_db_tests(engine):
    """Teste la frontière INSERT+liaison sur MariaDB, schémas uniques seulement."""
    from copy import deepcopy
    from uuid import uuid4
    from sqlalchemy import text
    import s5_tests as fixtures
    import s5_engineering as s5
    prefix='s5_test_controles_'+uuid4().hex[:12]
    layout=s5.Layout(prefix+'_gold',prefix+'_dq',prefix+'_target')
    token=fixtures._TEST_LAYOUT.set(layout)
    names=[layout.target,layout.gold,layout.dq]
    results=[]
    batch=fixtures.BATCH
    good=[{'ecart_bronze_silver':0,'ecart_silver_gold':0}]

    def history():
        with engine.connect() as cx:
            return s5.rows(cx,f'SELECT * FROM {s5.table(layout.dq,"dq_history")} ORDER BY id')

    def calculated(cx):
        n,e=map(int,cx.execute(text(f"SELECT COUNT(*),COALESCE(SUM(date_fin<=date_debut),0) FROM {s5.table(layout.gold,'contrat_certifie')} WHERE _batch_id=:b"),{'b':batch}).one())
        return [{'couche':layer,'rule_id':'RQ-001','table_logique':'contrat',
                 'nb_testees':n,'nb_echecs':e,'population':'Fixture synthétique datée'}
                for layer in ('SILVER','GOLD','BRONZE')]

    def normal():
        fixtures._reset(engine)
        before=len(history())
        with s5.coherent_connection(engine) as cx:
            bound=s5.control_content(cx,layout)
            result=controls._persist_and_attest(cx,batch,layout,calculated(cx),good,bound)
        assert len(history())==before+3
        with engine.connect() as cx:
            valid=s5.attestation_valid(cx,result['attestation'],batch,layout,
                s5.fingerprint_gold(cx,batch,layout),s5._history(cx,batch,layout),
                s5._catalogue(cx,layout),s5._manifest(cx,batch,layout))
        assert valid and result['attestation']['synthetique'] is True
        assert result['nombre_controles']==3
        return {'mesures_commitees':3,'attestation_valide':True}

    def rollback():
        fixtures._reset(engine)
        before=history();observed=[]
        def invalidate(cx,*args,**kwargs):
            observed.append(cx.execute(text(f'SELECT COUNT(*) FROM {s5.table(layout.dq,"dq_history")}')).scalar_one())
            return False
        try:
            with patch.object(s5,'attestation_valid',invalidate):
                with s5.coherent_connection(engine) as cx:
                    bound=s5.control_content(cx,layout)
                    controls._persist_and_attest(cx,batch,layout,calculated(cx),good,bound)
        except AssertionError as exc:
            assert 'Liaison des contrôles invalide' in str(exc)
        else:raise AssertionError('Une liaison invalide devait annuler les INSERT')
        assert observed==[len(before)+3] and history()==before
        return {'insertions_avant_panne':3,'historique_integralement_retabli':True}

    def inconsistent_conservation():
        fixtures._reset(engine)
        before=history()
        for field in ('ecart_bronze_silver','ecart_silver_gold','chevauchement','rejets_sans_bronze'):
            bad=deepcopy(good);bad[0][field]=1
            try:
                with s5.coherent_connection(engine) as cx:
                    bound=s5.control_content(cx,layout)
                    controls._persist_and_attest(cx,batch,layout,calculated(cx),bad,bound)
            except ValueError as exc:assert 'Conservation invalide' in str(exc)
            else:raise AssertionError('Conservation incohérente acceptée : '+field)
            assert history()==before
        return {'ecarts_et_chevauchements_refuses':4,'aucune_mesure_partielle':True}

    try:
        for name,test in [('historisation_liaison_commit',normal),
                          ('liaison_invalide_rollback_mesures',rollback),
                          ('conservation_invalide_avant_insert',inconsistent_conservation)]:
            results.append({'cas':name,'etat':'PASSE',**test()})
    finally:
        try:
            with engine.begin() as cx:
                for name in names:
                    assert name.startswith('s5_test_controles_')
                    cx.execute(text(f'DROP DATABASE IF EXISTS {s5.ident(name)}'))
        finally:
            fixtures._TEST_LAYOUT.reset(token)
    with engine.connect() as cx:
        assert all(not cx.execute(text('SELECT 1 FROM information_schema.schemata WHERE schema_name=:s'),{'s':name}).first() for name in names)
    return {'synthetique':True,'nombre_tests':len(results),'tous_passes':True,
            'schemas_nettoyes':True,'tests':results}
