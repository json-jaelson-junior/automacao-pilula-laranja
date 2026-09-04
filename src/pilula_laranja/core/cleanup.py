# Importações

from datetime import UTC, datetime, timedelta

from pilula_laranja.db.connection import TursoClient

PROCESSED_ITEMS_TTL_DAYS = 14
API_USAGE_TTL_HOURS = 72


def cleanup_processed_items(client: TursoClient, dry_run: bool = False) -> int:
    """Remove registros de processed_items mais antigos que o TTL

    Args:
        client: Instância autenticada do TursoClient
        dry_run: Se True, apenas conta os registros elegíveis sem apagar

    Returns:
        Quantidade de registros removidos (ou que seriam removidos, em dry_run)

    Raises:
        TursoError: Se a comunicação com o Turso falhar
    """

    cutoff = (datetime.now(UTC) - timedelta(days=PROCESSED_ITEMS_TTL_DAYS)).isoformat()

    rows = client.execute(
        "SELECT COUNT(*) AS total FROM processed_items WHERE created_at < ?",
        [cutoff],
    )
    total = int(rows[0]["total"])

    if dry_run or total == 0:
        return total

    client.execute(
        "DELETE FROM processed_items WHERE created_at < ?",
        [cutoff],
    )
    return total


def cleanup_api_usage(client: TursoClient, dry_run: bool = False) -> int:
    """Remove registros de api_usage mais antigos que o TTL

    Args:
        client: Instância autenticada do TursoClient
        dry_run: Se True, apenas conta os registros elegíveis sem apagar

    Returns:
        Quantidade de registros removidos (ou que seriam removidos, em dry_run)

    Raises:
        TursoError: Se a comunicação com o Turso falhar
    """

    cutoff = (datetime.now(UTC) - timedelta(hours=API_USAGE_TTL_HOURS)).isoformat()

    rows = client.execute(
        "SELECT COUNT(*) AS total FROM api_usage WHERE created_at < ?",
        [cutoff],
    )
    total = int(rows[0]["total"])

    if dry_run or total == 0:
        return total

    client.execute(
        "DELETE FROM api_usage WHERE created_at < ?",
        [cutoff],
    )
    return total
