# Importações
import structlog

from pilula_laranja.clients.wordpress import DraftPost, PublishResult, WordPressClient
from pilula_laranja.core.rewrite import RewriteResult
from pilula_laranja.utils.metadata import inject_metadata
from pilula_laranja.utils.sanitize import SanitizationError, sanitize_html

logger = structlog.get_logger()


def publish_item(
    result: RewriteResult,
    wp_client: WordPressClient,
) -> PublishResult:
    """Sanitiza, injeta metadata e cria rascunho no WP para um único item

    Args:
        result: RewriteResult com success=True vindo do rewrite_all
        wp_client: WordPressClient já instanciado

    Returns:
        PublishResult com post_id e post_url se sucesso,
        ou success=False com reason descrevendo erro
    """

    item = result.item

    try:
        clean_html = sanitize_html(result.body)
        final_content = inject_metadata(
            clean_html, url=item.url, source_name=item.source_name
        )
        post = DraftPost(
            title=item.title, content=final_content, excerpt=result.excerpt
        )
        return wp_client.create_draft(post)

    except SanitizationError as exc:
        logger.warning(
            "publish_sanitizacao_falhou",
            url=item.url,
            source=item.source_name,
            erro=str(exc),
        )
        return PublishResult(
            post_id=0,
            post_url="",
            success=False,
            reason=f"sanitization_error: {exc}",
        )


def publish_all(
    results: list[RewriteResult],
    wp_client: WordPressClient,
) -> list[PublishResult]:
    """Publica todos os RewriteResult aprovados como rascunhos no WordPress

    Args:
        results: lista de RewriteResult com success=True do rewrite_all
        wp_client: WordPressClient já instanciado

    Returns:
        Lista de PublishResult - inclui sucessos e falhas para rastreabilidade
    """

    publish_results = []
    failed = 0

    for result in results:
        pr = publish_item(result, wp_client)
        publish_results.append(pr)

        if not pr.success:
            failed += 1
            logger.info(
                "item_descartado_publish", url=result.item.url, reason=pr.reason
            )

    logger.info(
        "publish_concluido",
        total=len(results),
        sucesso=len(publish_results) - failed,
        falhas=failed,
    )

    return publish_results
