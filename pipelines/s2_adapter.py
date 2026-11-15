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
