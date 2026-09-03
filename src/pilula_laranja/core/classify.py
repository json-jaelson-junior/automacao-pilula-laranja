# Importações
import os
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

from pilula_laranja.clients.gemini import GeminiClient, GeminiQuotaError
from pilula_laranja.config import AppConfig
from pilula_laranja.core.extract import ExtractedItem

logger = structlog.get_logger()


@dataclass
class ClassifyResult:
    """Resultado da classificação semântica de um item

    Attributes:
        item: ExtractedItem avaliado pelo Gemini
        passed: True se o modelo considerou relevante
        reason: "semantic_approved", "semantic_rejected" ou
        "classify_error: <msg>"
    """

    item: ExtractedItem
    passed: bool
    reason: str


def _load_prompt_template() -> str:
    """Lê o arquivo prompts/classify.md relativo à raiz do projeto

    Returns:
        Conteúdo do template como string com placeholders {title} e {content}

    Raises:
        FileNotFoundError: se prompts/classify.md não existir
    """

    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "classify.md"
    return prompt_path.read_text(encoding="utf-8")


def _build_prompt(template: str, item: ExtractedItem) -> str:
    """Substitui os placeholders do template com os dados do item

    Args:
        template: string com placeholders {title} e {content}
        item: ExtractedItem com os dados reais

    Returns:
        Prompt pronto para enviar ao Gemini
    """

    return template.format(title=item.title, content=item.content[:4000])


def _parse_response(response: str) -> bool:
    """Interpreta a resposta do Gemini como booleano

    Args:
        response: texto bruto retornado por GeminiClient.generate()

    Returns:
        True se a resposta indica relevância, False caso contrário
    """

    return response.strip().upper().startswith("SIM")


def classify_item(
    item: ExtractedItem,
    client: GeminiClient,
    prompt_template: str,
    model: str,
) -> ClassifyResult:
    """Classifica semanticamente um único item usando o Gemini

    Args:
        item: item a classificar
        client: GeminiCliente já instanciado com db e config
        prompt_template: conteúdo de prompts/classify.md já carregado
        model: nome do modelo Gemini

    Returns:
        ClassifyResult com a decisão e o motivo
    """

    prompt = _build_prompt(prompt_template, item)

    try:
        response = client.generate(prompt=prompt, model=model, purpose="classify")
        passed = _parse_response(response)
        reason = "semantic_approved" if passed else "semantic_rejected"
        return ClassifyResult(item=item, passed=passed, reason=reason)
    except GeminiQuotaError:
        raise
    except Exception as exc:
        logger.warning(
            "classify_item_falhou",
            url=item.url,
            source=item.source_name,
            erro=str(exc),
        )
        return ClassifyResult(item=item, passed=False, reason=f"classify_error: {exc}")


def classify_all(
    items: list[ExtractedItem],
    client: GeminiClient,
    config: AppConfig,  # noqa: ARG001
) -> list[ExtractedItem]:
    """Classifica semanticamente uma lista de itens, retornando apenas os aprovados

    Args:
        items: lista de ExtractedItem que passaram pelo filter_all
        client: GeminiClient instanciado com db e config
        config: AppConfig - recebido por consistência de interface com filter_all

    Returns:
        Lista de ExtractedItem aprovados pelo classificador semântico
    """

    model = os.environ.get("GEMINI_CLASSIFIER_MODEL", "gemini-3.5-flash-lite")
    prompt_template = _load_prompt_template()
    sleep_seconds = 60 / config.gemini.classify_rpm
    max_items = config.gemini.classify_rpd // 5

    items_to_process = items[:max_items]

    passed = []
    rejected = 0

    for item in items_to_process:
        result = classify_item(item, client, prompt_template, model)

        if result.passed:
            passed.append(item)
            logger.info(
                "item_aprovado_semanticamente",
                url=item.url,
                source=item.source_name,
            )
        else:
            rejected += 1
            logger.info(
                "item_rejeitado_semanticamente",
                url=item.url,
                source=item.source_name,
                reason=result.reason,
            )

        time.sleep(sleep_seconds)

    logger.info(
        "classificacao_concluida",
        total=len(items),
        aprovados=len(passed),
        rejeitados=rejected,
    )

    return passed
