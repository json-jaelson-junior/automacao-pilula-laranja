# Importações
import os
from datetime import UTC, datetime
from typing import Any

import structlog
from google import genai
from google.genai import types
from tenacity import Retrying, stop_after_attempt, wait_exponential

from pilula_laranja.config import AppConfig
from pilula_laranja.db.connection import TursoClient

logger = structlog.get_logger()


class GeminiQuotaError(Exception):
    """Levantada quando uso diário de tokens atinge 80% do limite configurado"""

    pass


class GeminiClient:
    """Cliente centralizado para todas as chamadas à API do Gemini"""

    def __init__(self, db: TursoClient, config: AppConfig) -> None:
        """Autentica e configura o client com timeout global

        Args:
            db: instância do TursoClient para gravar e consultar api_usage
            config: AppConfig completo - apenas config.gemini é utilizado internamente

        Raises:
            ValueError: se GEMINI_API_KEY não estiver definida no ambiente
        """

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY é obrigatória - defina no .env")

        timeout_ms = config.gemini.timeout_seconds * 1000
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        self._db = db
        self._gemini_config = config.gemini

    def generate(self, prompt: str, model: str, purpose: str) -> str:
        """Ponto de entrada público para qualquer chamada ao Gemini

        Args:
            prompt: texto do prompt a enviar ao modelo
            model: nome do modelo (ex: "gemini-3.0-flash") - via env var no caller
            purpose: rótulo para auditoria em api_usage (ex: "classify", "rewrite")

        Returns:
            Texto da resposta gerada pelo modelo

        Raises:
            GeminiQuotaError: se uso diário >= 80% do limite configurado
            Exception: repropaga a última exceção após esgotar todas as tentativas
        """

        self._check_quota(model)
        response = self._call_api(prompt, model)
        tokens = response.usage_metadata.total_token_count or 0
        self._record_usage(model, tokens, purpose)
        logger.info("gemini_call_ok", model=model, purpose=purpose, tokens=tokens)
        return response.text

    def _check_quota(self, model: str) -> None:
        """Verifica se o uso de tokens de hoje está abaixo de 80% do limite

        Args:
            model: filtra por modelo - Flash e Pro têm limites independentes

        Raises:
            GeminiQuotaError: se tokens usados hoje >= 80% de daily_token_limit
        """

        today_start = (
            datetime.now(UTC)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
        )

        rows = self._db.execute(
            "SELECT SUM(CAST(tokens_used AS INTEGER)) as total FROM api_usage "
            "WHERE model = ? AND created_at >= ?",
            [model, today_start],
        )

        total = int(rows[0]["total"] or 0) if rows else 0
        limit = self._gemini_config.daily_token_limit
        threshold = int(limit * 0.8)

        if total >= threshold:
            logger.warning(
                "gemini_quota_alta",
                model=model,
                tokens_usados=total,
                limite=limit,
                threshold=threshold,
            )
            raise GeminiQuotaError(
                f"Quota acima de 80%: {total}/{limit} tokens usados hoje para '{model}'"
            )

    def _call_api(self, prompt: str, model: str) -> Any:
        """Executa a chamada real ao Gemini com retry e backoff exponencial

        Args:
            prompt: texto do prompt
            model: nome do modelo a invocar

        Returns:
            GenerateContentResponse do SDK - acesso via .text e .usage_metadata

        Raises:
            Exception: repropaga a exceção original após esgotar todas as tentativas
        """

        for attempt in Retrying(
            stop=stop_after_attempt(self._gemini_config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            reraise=True,
        ):
            with attempt:
                return self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                )

    def _record_usage(self, model: str, tokens: int, purpose: str) -> None:
        """Persiste o uso de tokens no banco após chamada bem-sucedida

        Args:
            model: modelo utilizado na chamada
            tokens: total de tokens consumidos (input + output)
            purpose: rótulo de auditoria
        """

        now = datetime.now(UTC).isoformat()
        self._db.execute(
            "INSERT INTO api_usage (model, tokens_used, purpose, created_at) "
            "VALUES (?, ?, ?, ?)",
            [model, str(tokens), purpose, now],
        )
        logger.debug("uso_registrado", model=model, tokens=tokens, purpose=purpose)
