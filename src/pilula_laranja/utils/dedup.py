# Importações
import hashlib
from datetime import UTC, datetime

import structlog

from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.db.connection import TursoClient, TursoError

logger = structlog.get_logger()


def compute_hash(url: str) -> str:
    """Calcula o SHA-256 da URL e retorna com string hexadecimal

    Args:
        url: URL do artigo a ser hasheada

    Returns:
        String de 64 caracteres hexadecimais representando o hash SHA-256
    """
    return hashlib.sha256(url.encode()).hexdigest()


def is_duplicate(client: TursoClient, url_hash: str) -> bool:
    """Verifica se um hash já existe na tabela processed_items

    Args:
        client: Instância autenticada do TursoClient
        url_hash: Hash SHA-256 da URL a verificar

    Returns:
        True se já existe, False se é novo
    """
    rows = client.execute(
        "SELECT 1 FROM processed_items WHERE url_hash = ? LIMIT 1",
        [url_hash],
    )
    return len(rows) > 0


def mark_processed(client: TursoClient, item: ExtractedItem, url_hash: str) -> None:
    """Insere um item na tabela processed_items marcando-o como coletado

    Args:
        client: Instância autenticada do TursoClient
        item: Item extraído a ser registrado
        url_hash: Hask SHA-256 já calculado da URL do item

    Raises:
        TursoError: Se a inserção do banco falhar
    """
    created_at = datetime.now(UTC).isoformat()

    client.execute(
        """
        INSERT INTO processed_items (url_hash, source_url, title, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [url_hash, item.url, item.title, "collected", created_at],
    )


def filter_new_items(
    client: TursoClient,
    items: list[ExtractedItem],
) -> list[ExtractedItem]:
    """Filtra itens já processados, registra os novos e retorna apenas os inéditos

    Para cada item:
      1. Calcula o hash da URL
      2. Verifica se já existe no banco
      3. Se novo: registra e mantém na lista de retorno
      4. Se duplicado: descarta e loga

    Args:
        client: Instância autenticada do TursoClient
        items: Lista de itens extraídos vindos do extractor

    Returns:
        Lista contendo apenas os itens ainda não processados
    """
    new_items: list[ExtractedItem] = []

    for item in items:
        url_hash = compute_hash(item.url)

        if is_duplicate(client, url_hash):
            logger.debug("item_duplicado", url=item.url, source=item.source_name)
            continue

        try:
            mark_processed(client, item, url_hash)
        except TursoError:
            logger.error(
                "falha_ao_registrar_item",
                url=item.url,
                source=item.source_name,
            )
            continue

        new_items.append(item)

    logger.info(
        "dedup_concluido",
        total_recebidos=len(items),
        total_novos=len(new_items),
        total_descatados=len(items) - len(new_items),
    )

    return new_items
