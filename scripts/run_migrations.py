# Importações
from dotenv import load_dotenv

from pilula_laranja.db.connection import TursoClient
from pilula_laranja.db.migrations import run_migrations

load_dotenv()  # carrega o .env

client = TursoClient()
run_migrations(client)
