# Importações
from __future__ import annotations

import logging
from datetime import UTC, datetime

import requests
import trafilatura
from pydantic import BaseModel
from readability import Document

from pilula_laranja.core.collect import RawItem

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
_MIN_CONTENT_LENGTH = 200
_REQUEST_TIMEOUT = 15


class ExtractedItem(BaseModel):
    """Artigo com conteúdo completo extraído, pronto para filtragem"""

    source_name: str
    title: str
    url: str
    published_at: datetime | None
    summary: str
    content: str
    extracted_at: datetime


def _fetch_html(url: str) -> str | None:
    """Busca HTML bruto de uma URL com request

    Returns:
        HTML como string ou None em caso de falha
    """

    try:
        response = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Falha ao buscar URL | url=%s erro=%s", url, exc)
        return None


def _extract_with_trafilatura(html: str, url: str) -> str | None:
    """Tenta extrair conteúdo com trafilatura"""

    content = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        no_fallback=True,
    )

    if not content or len(content) < _MIN_CONTENT_LENGTH:
        return None

    return content


def _extract_with_readability(html: str) -> str | None:
    """Fallback: tenta extrair conteúdo com readability-lxml"""

    try:
        doc = Document(html)
        content = doc.summary(html_partial=True)
        if not content or len(content) < _MIN_CONTENT_LENGTH:
            return None
    except Exception as exc:
        logger.warning("Falha no readability | erro=%s", exc)
        return None


def extract_item(item: RawItem) -> ExtractedItem | None:
    """Extrai conteúdo completo de um RawItem

    Tenta trafilatura primeiro, readability como fallback
    Retorna None se nenhum método extrair conteúdo suficiente

    Args:
        item: item bruto coletado do feed RSS

    Returns:
        ExtractedItem com conteúdo completo ou None
    """

    logger.info("Extraindo artigo | source=%s url=%s", item.source_name, item.url)

    html = _fetch_html(item.url)
    if html is None:
        return None

    content = _extract_with_trafilatura(html, item.url)

    if content is None:
        logger.info(
            "Trafilatura sem resultado, tentando readability | url=%s", item.url
        )
        content = _extract_with_readability(html)

    if content is None:
        logger.warning("Extração falhou em ambos os métodos | url=%s", item.url)
        return None

    return ExtractedItem(
        source_name=item.source_name,
        title=item.title,
        url=item.url,
        published_at=item.published_at,
        summary=item.summary,
        content=content,
        extracted_at=datetime.now(UTC),
    )


def extract_all(items: list[RawItem]) -> list[ExtractedItem]:
    """Extrai conteúdo de uma lista de RawItems

    Args:
        items: lista de itens brutos do coletor

    Returns:
        Lista de ExtractedItem, itens com falha de extração são descartados
    """

    extracted = []
    for item in items:
        result = extract_item(item)
        if result is not None:
            extracted.append(result)
        else:
            logger.warning("Item descartado por falha na extração | url=%s", item.url)

    logger.info(
        "Extração concluída | total=%d extraídos=%d descartados=%d",
        len(items),
        len(extracted),
        len(items) - len(extracted),
    )

    return extracted
