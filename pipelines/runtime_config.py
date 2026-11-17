"""Configuration locale partagée ; aucune valeur de repli pour les secrets."""
from pathlib import Path
import os
from dotenv import load_dotenv, dotenv_values
from sqlalchemy.engine import URL


ENV_FILE = Path(__file__).resolve().parents[1] / ".venv" / ".env"

def load_local_env():
    """Charger le fichier .venv/.env local sans écraser les variables du processus."""
    load_dotenv(ENV_FILE, override=False, interpolate=False)


def required_env(name):
    value = _settings().get(name)
    if not value:
        raise ValueError(f"Variable d’environnement requise absente : {name}")
    return value


def _settings():
    local = dotenv_values(ENV_FILE, interpolate=False) if ENV_FILE.is_file() else {}
    return {**local, **os.environ}


def database_url(schema=None, *, reader=False):
    settings = _settings()
    override = settings.get("DQ_DATABASE_URL" if reader else "DQ_DB_URL")
    if override:
        # Conserver intégralement les URLs explicitement fournies.
        return override
    else:
        url = URL.create(
            "mysql+pymysql",
            username=settings.get("DQ_READER_USER", "reader") if reader else settings.get("DQ_DB_USER", "root"),
            password=required_env("DQ_READER_PASSWORD" if reader else "MARIADB_ROOT_PASSWORD"),
            host=settings.get("DQ_DB_HOST", "127.0.0.1"),
            port=int(settings.get("DQ_DB_PORT", "3306")),
            database=schema,
        )
    return url.render_as_string(hide_password=False)
