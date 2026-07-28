from datetime import UTC, datetime

import structlog

logger = structlog.get_logger()

_AUDIT_COMMENT_TEMPLATE = (
    "\n<!-- PILULA_LARANJA:"
    " published_at={published_at}"
    " source_name={source_name}"
    " url={url}"
    " -->"
)

_DISCLAIMER_TEMPLATE = (
    "\n<p><em>Este artigo é uma adaptação editorial de"
    ' <a href="{url}" rel="noopener noreferrer">{source_name}</a>.'
    " Conteúdo revisado manualmente antes da publicação.</em></p>"
)


def inject_metadata(html: str, url: str, source_name: str) -> str:
    """Injeta comentário de auditoria e disclaimer de fonte no HTML sanitizado

    Deve ser chamado APÓS sanitize_html() - bleach removeria os comentários
    se chamado antes (strip_comments=True)

    Args:
        html: HTML já sanitizado pelo sanitize_html()
        url: URL canônica do artigo original
        source_name: nome legível da fonte (ex: "Bitcoin Magazine")

    Returns:
        HTML com disclaimer visível e comentário de auditoria ao final
    """

    published_at = datetime.now(UTC).isoformat()

    audit_comment = _AUDIT_COMMENT_TEMPLATE.format(
        published_at=published_at,
        source_name=source_name,
        url=url,
    )

    disclaimer = _DISCLAIMER_TEMPLATE.format(
        url=url,
        source_name=source_name,
    )

    result = html + disclaimer + audit_comment

    logger.debug(
        "metadata_injetado", source_name=source_name, published_at=published_at
    )

    return result
