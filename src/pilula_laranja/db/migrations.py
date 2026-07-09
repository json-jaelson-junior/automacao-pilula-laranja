# Importações
from pilula_laranja.db.connection import TursoClient, TursoError

# SQL de criação das tabelas
# IF NOT EXISTS: idempotente (pode rodar várias vezes sem erro)
CREATE_PROCESSED_ITEMS = """
CREATE TABLE IF NOT EXISTS processed_items (
    id          INTEGER PRIMARY KEY,
    url_hash    TEXT    NOT NULL UNIQUE,
    source_url  TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'collected',
    created_at  TEXT    NOT NULL
)
"""

CREATE_API_USAGE = """
CREATE TABLE IF NOT EXISTS api_usage (
    id          INTEGER PRIMARY KEY,
    model       TEXT    NOT NULL,
    tokens_used TEXT    NOT NULL DEFAULT 0,
    purpose     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
)
"""


def run_migrations(client: TursoClient) -> None:
    """Cria as tabelas se ainda não existirem

    Args:
        client: Instância autenticada do TursoClient

    Raises:
        TursoError: Se alguma migration falhar
    """

    migrations = [
        ("processed_items", CREATE_PROCESSED_ITEMS),
        ("api_usage", CREATE_API_USAGE),
    ]

    for name, sql in migrations:
        try:
            client.execute(sql)
            print(f"[migration] OK: {name}")
        except TursoError as e:
            print(f"[migration] ERRO em {name}: {e}")
            raise
