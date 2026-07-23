# Importações
import bleach
import structlog

logger = structlog.get_logger()


ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "a",
        "strong",
        "em",
        "blockquote",
        "code",
        "pre",
    }
)

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "rel"],
}

MIN_CONTENT_LENGTH = 200


class SanitizationError(Exception):
    """Levantada quando o HTML sanitizado fica vazio ou abaixo do mínimo útil"""

    pass


def sanitize_html(html: str) -> str:
    """Sanitiza HTML removendo tags e atributos fora do allowlist do projeto

    Usa bleach com allowlist restritiva para garantir que nenhum conteúdo
    perigoso (script, ifram, on*, javascript:) chegue ao WordPress

    Links com esquemas não-HTTP são removidos pela bleach automaticamente

    Args:
        html: string HTML bruta - tipicamente output do Gemini rewriter

    Returns:
        HTML sanitizado, seguro para publicação no WordPress

    Raises:
        SanitizationError: se o conteúdo resultante for vazio ou muito curto
    """

    if not html or not html.strip():
        raise SanitizationError("HTML de entrada está vazio")

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True,
    )

    content_length = len(cleaned.strip())

    if content_length < MIN_CONTENT_LENGTH:
        logger.warning(
            "sanitizacao_conteudo_curto",
            tamanho=content_length,
            minimo=MIN_CONTENT_LENGTH,
        )
        raise SanitizationError(
            f"Conteúdo sanitizado muito curto: {content_length} chars "
            f"(mínimo: {MIN_CONTENT_LENGTH})"
        )

    logger.debug(
        "sanitizacao_ok", tamanho_original=len(html), tamanho_final=content_length
    )
    return cleaned
