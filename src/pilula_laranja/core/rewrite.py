# Importações
import os
import time
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

import structlog

from pilula_laranja.clients.gemini import GeminiClient, GeminiQuotaError
from pilula_laranja.config import AppConfig
from pilula_laranja.core.extract import ExtractedItem

logger = structlog.get_logger()


@dataclass
class RewriteResult:
    """Resultado da reescrita de um item pelo Gemini

    Attributes:
        item: ExtractedItem original
        excerpt: resumo SEO em texto puro, máx 20 chars
        body: HTML do corpo da notícia, ainda bruto
        success: False se o Gemini falhou ou o parse não encontrou o separador
        reason: "rewrite_ok", "rewrite_error: <msg>" ou "rewrite_parse_error"
    """

    item: ExtractedItem
    excerpt: str
    body: str
    success: bool
    reason: str


def _load_prompt_template() -> str:
    """Lê prompts/news_rewrite.md relativo à raiz do projeto

    Returns:
        Conteúdo do template com placeholders {title}, {content}, {url},
        {source_name}

    Raises:
        FileNorFoundError: se o arquivo não existir
    """

    prompt_path = (
        Path(__file__).parent.parent.parent.parent / "prompts" / "news_rewrite.md"
    )
    return prompt_path.read_text(encoding="utf-8")


def _build_prompt(template: str, item: ExtractedItem) -> str:
    """Substitui os 4 placeholders do template com os dados do item

    Args:
        template: string com placeholders {title}, {content}, {url},
    {source_name}
        item: ExtractedItem com os dados reais do artigo

    Returns:
        Prompt pronto para enviar ao Gemini
    """

    return template.format(
        title=item.title,
        content=item.content[:4000],
        url=item.url,
        source_name=item.source_name,
    )


def _parse_response(response: str) -> tuple[str, str]:
    """Separa excerpt e body usando o separador contratual do prompt

    Args:
        response: texto bruto retornado pelo Gemini

    Returns:
        Tuple (excerpt, body)

    Raises:
        ValueError: se o separador ---SEO--- não estiver presente
    """

    if "---SEO---" not in response:
        raise ValueError("Separador ---SEO--- ausente na resposta do Gemini")

    parts = response.split("---SEO---", maxsplit=1)
    excerpt = parts[0].strip()
    body = parts[1].strip()

    return excerpt, body


def _interleave_by_source(items: list[ExtractedItem]) -> list[ExtractedItem]:
    """Intercala itens por fonte, alternando 1 a 1 entre as fontes disponíveis.

    Agrupa por source_name preservando a ordem de chegada dentro de cada
    grupo, depois usa zip_longest para distribuir round-robin: 1 item da
    fonte A, 1 da B, 1 da C, 1 da D, volta pra A, e assim por diante — até
    esgotar todas. Evita que uma única fonte domine o corte de max_items.

    Args:
        items: lista de ExtractedItem já aprovados pelo classify_all

    Returns:
        Mesma lista, reordenada para intercalar fontes
    """
    groups: dict[str, list[ExtractedItem]] = {}
    for item in items:
        groups.setdefault(item.source_name, []).append(item)

    interleaved = []
    for row in zip_longest(*groups.values(), fillvalue=None):
        interleaved.extend(item for item in row if item is not None)

    return interleaved


def rewrite_item(
    item: ExtractedItem,
    client: GeminiClient,
    prompt_template: str,
    model: str,
) -> RewriteResult:
    """Reescreve um único item usando o Gemini

    Args:
        item: item aprovado pelo classify_all
        client: GeminiClient já instanciado
        prompt_template: conteúdo de prompts/news_rewrite.ms já carregado
        model: nome do modelo Gemini

    Returns:
        RewriteResult com success=True e excerpt+body preenchidos, ou
        success=False com reason descrevendo o erro
    """

    prompt = _build_prompt(prompt_template, item)

    try:
        response = client.generate(prompt=prompt, model=model, purpose="rewrite")
        excerpt, body = _parse_response(response)
        logger.info("item_reescrito", url=item.url, source=item.source_name)
        return RewriteResult(
            item=item,
            excerpt=excerpt,
            body=body,
            success=True,
            reason="rewrite_ok",
        )

    except GeminiQuotaError:
        raise

    except ValueError as exc:
        logger.warning(
            "rewrite_parse_error",
            url=item.url,
            source=item.source_name,
            erro=str(exc),
        )
        return RewriteResult(
            item=item,
            excerpt="",
            body="",
            success=False,
            reason=f"rewrite_parse_error: {exc}",
        )

    except Exception as exc:
        logger.warning(
            "rewrite_item_falhou",
            url=item.url,
            source=item.source_name,
            erro=str(exc),
        )
        return RewriteResult(
            item=item,
            excerpt="",
            body="",
            success=False,
            reason=f"rewrite_error: {exc}",
        )


def rewrite_all(
    items: list[ExtractedItem],
    client: GeminiClient,
    config: AppConfig,
) -> list[RewriteResult]:
    """Reescreve uma lista de itens, retornando apenas os bem-sucedidos

    Args
        items: lista de ExtractedItem aprovados pelo classify_all
        client: GeminiClient instanciado com db e config

    Returns:
        Lista de RewriteResult com success=True
    """

    model = os.environ.get("GEMINI_REWRITER_MODEL", "gemini-3.8-flash")
    prompt_template = _load_prompt_template()
    sleep_seconds = 60 / config.gemini.rewrite_rpm
    max_items = config.gemini.rewrite_rpd // 2

    items_to_process = _interleave_by_source(items)[:max_items]

    succeeded = []
    failed = 0

    for item in items_to_process:
        result = rewrite_item(item, client, prompt_template, model)

        if result.success:
            succeeded.append(result)
        else:
            failed += 1
            logger.info(
                "item_descartado_reescrita",
                url=item.url,
                source=item.source_name,
                reason=result.reason,
            )

        time.sleep(sleep_seconds)

    logger.info(
        "reescrita_concluida",
        total=len(items),
        sucesso=len(succeeded),
        falhas=failed,
    )

    return succeeded
