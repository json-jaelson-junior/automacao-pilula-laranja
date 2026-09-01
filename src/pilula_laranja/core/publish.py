# Importações
import re

import structlog

from pilula_laranja.clients.wordpress import DraftPost, PublishResult, WordPressClient
from pilula_laranja.core.rewrite import RewriteResult
from pilula_laranja.utils.metadata import inject_metadata
from pilula_laranja.utils.sanitize import SanitizationError, sanitize_html

logger = structlog.get_logger()


def _extract_title(html: str) -> tuple[str, str]:
    match = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return "", html
    title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
    body = (html[: match.start()] + html[match.end() :]).strip()
    return title, body


def _to_gutenberg_blocks(html: str) -> str:
    block_map = {
        "p": ("<!-- wp:paragraph -->", "<!-- /wp:paragraph -->"),
        "h2": ('<!-- wp:heading {"level":2} -->', "<!-- /wp:heading -->"),
        "h3": ('<!-- wp:heading {"level":3} -->', "<!-- /wp:heading -->"),
        "h4": ('<!-- wp:heading {"level":4} -->', "<!-- /wp:heading -->"),
        "ul": ("<!-- wp:list -->", "<!-- /wp:list -->"),
        "ol": ('<!-- wp:list {"ordered":true} -->', "<!-- /wp:list -->"),
        "blockquote": ("<!-- wp:quote -->", "<!-- /wp:quote -->"),
    }

    def _wrap(match: re.Match) -> str:
        tag = match.group(1).lower()
        full_element = match.group(0)
        if tag in block_map:
            open_c, close_c = block_map[tag]
            return f"{open_c}\n{full_element}\n{close_c}"
        return full_element

    pattern = re.compile(
        r"<(p|h2|h3|h4|ul|ol|blockquote)[\s>].*?</\1>",
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(_wrap, html)


def publish_item(
    result: RewriteResult,
    wp_client: WordPressClient,
) -> PublishResult:
    item = result.item

    try:
        pt_title, body_sem_h2 = _extract_title(result.body)
        title = pt_title if pt_title else item.title
        clean_html = sanitize_html(body_sem_h2)
        gutenberg_html = _to_gutenberg_blocks(clean_html)
        final_content = inject_metadata(
            gutenberg_html, url=item.url, source_name=item.source_name
        )
        post = DraftPost(title=title, content=final_content, excerpt=result.excerpt)
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
