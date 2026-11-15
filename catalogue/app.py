"""Catalogue de métadonnées : le YAML est l'unique source, sans accès DB."""
from pathlib import Path
import os
import yaml
import streamlit as st


def load_catalogue(path):
    with Path(path).open(encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or not isinstance(data.get('tables'), dict) or not data['tables']:
        raise ValueError('Le catalogue doit contenir un dictionnaire tables non vide.')
    roles = data.get('roles')
    if not isinstance(roles, dict) or not all(
        isinstance(role, str) and isinstance(person, str) and person.strip()
        for role, person in roles.items()
    ):
        raise ValueError('Le champ roles doit associer des identifiants à des noms non vides.')
    for name, table in data['tables'].items():
        if not isinstance(name, str) or not isinstance(table, dict):
            raise ValueError(f'Fiche invalide : {name}')
        for field in ('couche', 'description', 'proprietaire', 'steward'):
            if not isinstance(table.get(field), str) or not table[field].strip():
                raise ValueError(f'{name} : champ {field} absent ou texte invalide')
        for field in ('proprietaire', 'steward'):
            if table[field] not in roles:
                raise ValueError(f'{name} : rôle inconnu {table[field]}')
        for field in ('regles', 'lineage', 'decisions'):
            values = table.get(field, [] if field == 'decisions' else None)
            if (not isinstance(values, list) or
                    (field != 'decisions' and not values) or
                    not all(isinstance(value, str) and value.strip() for value in values)):
                raise ValueError(f'{name} : {field} doit être une liste de textes')
        definitions = table.get('definitions', {})
        if not isinstance(definitions, dict) or not all(
            isinstance(label, str) and isinstance(value, str)
            for label, value in definitions.items()
        ):
            raise ValueError(f'{name} : definitions doit être un dictionnaire de textes')
    return data


def main():
    st.set_page_config(page_title='Catalogue AssurConnect')
    st.title('Catalogue AssurConnect')
    try:
        data = load_catalogue(os.getenv('DQ_CATALOGUE_PATH', str(Path(__file__).with_name('catalogue.yml'))))
    except (OSError, ValueError, yaml.YAMLError) as error:
        st.error(f'Catalogue indisponible : {error}')
        return
    st.caption(f"Lot de référence : {data.get('lot_de_reference', 'non renseigné')}")
    name = st.selectbox('Objet Gold', list(data['tables']))
    table = data['tables'][name]
    st.subheader(name)
    st.write(f"Couche : {table['couche']}")
    st.write(table['description'])
    st.write(f"Propriétaire : {data['roles'][table['proprietaire']]}")
    st.write(f"Data Steward : {data['roles'][table['steward']]}")
    st.subheader('Définitions')
    for field in ('grain', 'cle', 'sensibilite'):
        if field in table:
            st.write(f"{field} : {table[field]}")
    for label, definition in table.get('definitions', {}).items():
        st.write(f'{label} : {definition}')
    st.subheader('Règles de qualité')
    st.write(', '.join(table['regles']))
    if table.get('decisions'):
        st.write('Décisions : ' + ', '.join(table['decisions']))
    st.subheader('Lineage')
    for line in table['lineage']:
        st.write(line)


if __name__ == '__main__':
    main()
