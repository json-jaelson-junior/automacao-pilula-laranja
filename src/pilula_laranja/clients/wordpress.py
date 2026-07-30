import os
from dataclasses import dataclass

import requests
import structlog
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from pilula_laranja.utils.retry import _is_retryable_http_error, _log_before_sleep

logger = structlog.get_logger()


@dataclass
class DraftPost:
    """Dados prontos para criar um rascunho no WordPress

    Attributes:
        title: título reescrito pelo Gemini
        content: HTML sanitizado + metadata invisível + linha de Fonte
        excerpt: resumo SEO em texto puro (máx 250 chars)
    """

    title: str
    content: str
    excerpt: str


@dataclass
class PublishResult:
    """Resultado da tentativa de publicação de um rascunho

    Attributes:
        post_id: ID numérico do post no WP (0 se falhou)
        post_url: URL legível do rascunho (vazia se falhou)
        success: True se o rascunho foi criado com sucesso
        reason: "publish_ok" ou "publish_error: <msg>"
    """

    post_id: int
    post_url: str
    success: bool
    reason: str


class WordPressClient:
    """Cliente HTTP para a REST API do WordPress

    Autenticação via App Password (Basic Auth). Role mínima: Author
    Env vars obrigatórios: WP_URL, WP_USERNAME e WP_APP_PASSWORD
    """

    def __init__(self) -> None:
        url = os.environ["WP_URL"]
        username = os.environ["WP_USERNAME"]
        app_password = os.environ["WP_APP_PASSWORD"]

        self._base_url = url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = (username, app_password)
        self._session.headers.update({"Content-Type": "application/json"})

    def create_draft(self, post: DraftPost) -> PublishResult:
        """Cria um rascunho no WordPress via REST API

        Args:
            post: DraftPost com title, content e excerpt prontos

        Returns:
            PublishResult com post_id e post_url se sucesso,
            ou success=False com reason descrevendo o erro
        """

        endpoint = f"{self._base_url}/wp-json/wp/v2/posts"  # alterar junto com domínio

        payload = {
            "title": post.title,
            "content": post.content,
            "excerpt": post.excerpt,
            "status": "draft",
        }

        try:
            for attempt in Retrying(
                retry=retry_if_exception(_is_retryable_http_error),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=30),
                before_sleep=_log_before_sleep,
                reraise=True,
            ):
                with attempt:
                    response = self._session.post(endpoint, json=payload, timeout=30)
                    response.raise_for_status()

            data = response.json()
            post_id = data["id"]
            post_url = data["link"]

            logger.info(
                "rascunho_criado", post_id=post_id, post_url=post_url, title=post.title
            )

            return PublishResult(
                post_id=post_id, post_url=post_url, success=True, reason="publish_ok"
            )

        except Exception as exc:
            logger.warning("rascunho_falhou", title=post.title, erro=str(exc))
            return PublishResult(
                post_id=0, post_url="", success=False, reason=f"publish_error: {exc}"
            )
