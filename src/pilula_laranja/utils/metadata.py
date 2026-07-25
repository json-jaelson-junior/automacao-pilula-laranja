from datetime import UTC, datetime

import structlog

logger = structlog.get_logger()

_AUDIT_COMMENT_TEMPLATE = (
    "\n<!-- PILULA_LARANJA: gerado_em={gerado_em} fonte_nome={fonte_nome} -->"
)

_DISCLAIMER_TEMPLATE = (
    "\n<p><em>Este artigo é uma adaptação editorial de"
    ' <a href="{fonte_url}" rel="noopener noreferrer">{fonte_nome}</a>.'
    " Conteúdo revisado manualmente antes da publicação.</em></p>"
)


def inject_metadata(html: str, fonte_url: str, fonte_nome: str) -> str:
    """Injeta comentário de auditoria e disclaimer de fonte no HTML sanitizado

    Deve ser chamado APÓS sanitize_html() - bleach removeria os comentários
    se chamado antes (strip_comments=True)

    Args:
        html: HTML já sanitizado pelo sanitize_html()
        fonte_url: URL canônica do artigo original
        fonte_nome: nome legível da fonte (ex: "Bitcoin Magazine")

    Returns:
        HTML com disclaimer visível e comentário de auditoria ao final
    """

    gerado_em = datetime.now(UTC).isoformat()

    audit_comment = _AUDIT_COMMENT_TEMPLATE.format(
        gerado_em=gerado_em,
        fonte_nome=fonte_nome,
        fonte_url=fonte_url,
    )

    disclaimer = _DISCLAIMER_TEMPLATE.format(
        fonte_url=fonte_url,
        fonte_nome=fonte_nome,
    )

    result = html + disclaimer + audit_comment

    logger.debug("metadata_injetado", fonte_nome=fonte_nome, gerado_em=gerado_em)

    return result
