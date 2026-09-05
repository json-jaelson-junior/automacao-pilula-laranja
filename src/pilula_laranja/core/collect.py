# Importações
from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
import structlog
from pydantic import BaseModel

from pilula_laranja.config import AppConfig

logger = structlog.get_logger()


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
        logger.warning(
            "entrada_ignorada", motivo="titulo_ou_url_ausente", source=source_name
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

    logger.info("buscando_feed", source=source_name, url=feed_url)

    parsed = feedparser.parse(feed_url)
    if parsed.bozo:
        logger.warning(
            "feed_xml_mal_formado",
            source=source_name,
            erro=str(parsed.bozo_exception),
        )

    items = []
    for entry in parsed.entries:
        item = _parse_entry(entry, source_name)
        if item is not None:
            items.append(item)

    logger.info("feed_coletado", source=source_name, total=len(items))
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
            logger.info("fonte_ignorada", motivo="inativa", source=source.name)
            continue

        try:
            items = fetch_feed(source.name, str(source.feed_url))
            all_items.extend(items)
        except Exception as exc:
            logger.error("falha_ao_coletar_feed", source=source.name, erro=str(exc))

    logger.info("coleta_concluida", total_itens=len(all_items))
    return all_items
