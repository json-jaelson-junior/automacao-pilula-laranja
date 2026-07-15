# Importações
from dataclasses import dataclass

import structlog

from pilula_laranja.config import AppConfig
from pilula_laranja.core.extract import ExtractedItem

logger = structlog.get_logger()


@dataclass
class FilterResult:
    """Resultado da filtragem local de um item

    Attributes:
        item: o ExtractedItem avaliado
        passed: True se passou em todos os filtros
        reason: motivo da rejeição ou "passed"
    """

    item: ExtractedItem
    passed: bool
    reason: str


def _normalize(text: str) -> str:
    """Normaliza texto para comparação: lowercase e strip de espaços"""
    return text.lower().strip()


def check_blocklist(text: str, terms: list[str]) -> str | None:
    """Verifica se o texto contém algum termo da blocklist

    Args:
        text: texto normalizado para checar
        terms: lista de termos bloqueados

    Returns:
        Primeiro termo encontrado ou None
    """
    normalized = _normalize(text)
    for term in terms:
        if _normalize(term) in normalized:
            return term
    return None


def check_required_keywords(text: str, keywords: list[str]) -> bool:
    """Verifica se o texto contém ao menos uma keyword obrigatória

    Args:
        text: texto para checar
        keywords: lista de keywords obrigatórias

    Returns:
        True se ao menos uma keyword estiver presente
    """
    normalized = _normalize(text)
    return any(_normalize(kw) in normalized for kw in keywords)


def apply_filters(item: ExtractedItem, config: AppConfig) -> FilterResult:
    """Aplica blocklist e keyword filter em um único item

    Args:
        item: item extraído a ser avaliado
        config: configuração com blocklist e keywords

    Returns:
        FilterResult com decisão e motivo
    """
    full_text = f"{item.title} {item.content}"

    matched_term = check_blocklist(full_text, config.blocklist.terms)
    if matched_term is not None:
        return FilterResult(
            item=item, passed=False, reason=f"blocklist_match: {matched_term}"
        )

    if not check_required_keywords(full_text, config.keywords.required):
        return FilterResult(item=item, passed=False, reason="no_required_keyword")

    return FilterResult(item=item, passed=True, reason="passed")


def filter_all(
    items: list[ExtractedItem],
    config: AppConfig,
) -> list[ExtractedItem]:
    """Aplice filtros locais em uma lista de itens

    Args:
        items: lista de itens extraídos
        config: configuração com blocklist e keywords

    Returns:
        Lista de itens que passaram em todos os filtros
    """
    passed = []
    rejected = 0

    for item in items:
        result = apply_filters(item, config)
        if result.passed:
            passed.append(item)
            logger.info("item_aprovado", url=item.url, source=item.source_name)
        else:
            rejected += 1
            logger.info(
                "item_rejeitado",
                url=item.url,
                source=item.source_name,
                reason=result.reason,
            )

    logger.info(
        "filtragem_concluida",
        total=len(items),
        aprovados=len(passed),
        rejeitados=rejected,
    )

    return passed
