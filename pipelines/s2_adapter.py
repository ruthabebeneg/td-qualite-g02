"""Paramètres et populations partagés des contrôles S2."""
import os
import pandas as pd


def comparison_date():
    return pd.Timestamp(os.environ.get('DQ_COMPARISON_DATE') or pd.Timestamp.today()).normalize()


def normalized_type(values):
    return (values.astype('string').str.normalize('NFKD')
            .str.encode('ascii', errors='ignore').str.decode('ascii').str.strip().str.lower())


def physical_subscribers(frame):
    reason = frame['raison_sociale'].astype('string').str.strip()
    return (frame['client_id'].notna()
            & normalized_type(frame['type_personne']).eq('souscripteur')
            & (reason.isna() | reason.eq(''))).fillna(False)


def silver_clients(frame):
    """Projection CRM uniquement : source_id porte la clé client du contrat."""
    result = frame.loc[frame.source_systeme.eq('crm')].copy()
    result = result.rename(columns={'source_id': 'client_id', 'pays_iso': 'pays',
                                    'telephone_normalise': 'telephone'})
    # Nature PP/PM explicite ; une nature inconnue reste hors population PP.
    result['raison_sociale'] = result['nature_personne'].map({'PP': '', 'PM': 'PERSONNE MORALE'}).fillna('NATURE INCONNUE')
    return result


def gold_clients(frame):
    """Projection Gold sans lecture Silver ; conserver cli_id et les statuts métier."""
    result = frame.copy()
    result['client_id'] = result['cli_id']
    result['pays'] = result['pays_iso']
    result['type_personne'] = result['statut_client'].map({
        'ACTIF': 'souscripteur', 'INACTIF': 'souscripteur', 'A_REVOIR': 'souscripteur',
        'ASSURE': 'assure', 'PROSPECT': 'prospect'})
    return result


def gold_age_population(clients, contracts):
    """RQ002 : seules les PM identifiées sont exclues ; inconnu/absent échoue."""
    valid_key = clients.cli_id.notna() & clients.cli_id.astype('string').str.strip().ne('')
    unique = clients.loc[valid_key & ~clients.cli_id.duplicated(keep=False),
                         ['cli_id', 'nature_personne', 'date_naissance']]
    # Une référence vide ne doit jamais être rapprochée d'une clé vide.
    result = contracts.merge(unique, how='left', left_on='cli_souscripteur', right_on='cli_id')
    result = result.loc[result.nature_personne.ne('PM').fillna(True)].copy()
    start = pd.to_datetime(result.date_debut, errors='coerce')
    birth = pd.to_datetime(result.date_naissance, errors='coerce')
    age = start.dt.year - birth.dt.year - ((start.dt.month < birth.dt.month) |
           ((start.dt.month == birth.dt.month) & (start.dt.day < birth.dt.day))).astype(int)
    ok = result.nature_personne.eq('PP') & start.notna() & birth.notna() & age.ge(18)
    return result, ok.fillna(False)
