# Importações
from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
from pydantic import BaseModel

from pilula_laranja.config import AppConfig

logger = logging.getLogger(__name__)


class RawItem(BaseModel):
    """Item bruto coletado do feed RSS, antes de filtrar"""

    source_name: str
    title: str
    url: str
    published_at: datetime | None
    summary: str


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(UTC)
            except Exception:
                continue
    return None


def _parse_entry(entry: feedparser.FeedParserDict, source_name: str) -> RawItem | None:
    title = entry.get("title", "").strip()
    url = entry.get("link", "").strip()

    if not title or not url:
        logging.warning(
            "Entrada ignorada: título ou URL ausente | source=%s", source_name
        )
        return None

    summary = entry.get("summary", "").strip()
    published_at = _parse_date(entry)

    return RawItem(
        source_name=source_name,
        title=title,
        url=url,
        published_at=published_at,
        summary=summary,
    )


def fetch_feed(source_name: str, feed_url: str) -> list[RawItem]:
    """Busca e parseia um feed RSS

    Args:
        source_name: nome legível da fonte (para logs)
        feed_url: URL do feed RSS como string

    Returns:
        Lista de RawItem extraídos do feed
    """
    logger.info("Buscando feed | source=%s url=%s", source_name, feed_url)
    parsed = feedparser.parse(feed_url)

    if parsed.bozo:
        logger.warning(
            "Feed com XML mal formad | source=%s erro=%s",
            source_name,
            parsed.bozo_exception,
        )

    items = []
    for entry in parsed.entries:
        item = _parse_entry(entry, source_name)
        if item is not None:
            items.append(item)

    logger.info("Feed coletado | source=%s total=%d", source_name, len(items))
    return items


def collect_all(config: AppConfig) -> list[RawItem]:
    """Coleta todos os feeds ativos e retorna lista unificada de RawItems

    Args:
        config: configuração carregada e validade pelo config loader

    Returns:
        Lista de RawItem de todas as fontes ativas
    """
    all_items: list[RawItem] = []

    for source in config.sources:
        if not source.active:
            logger.info("Fonte ignorada (inativa) | source=%s", source.name)
            continue

        try:
            items = fetch_feed(source.name, str(source.feed_url))
            all_items.extend(items)
        except Exception as exc:
            logger.error(
                "Falha ao coletar feed | source=%s erro=%s",
                source.name,
                exc,
            )

    logger.info("Coleta concluída | total=%d itens", len(all_items))
    return all_items
