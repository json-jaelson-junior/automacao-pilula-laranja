# Importações
import requests
import structlog
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()


def _is_retryable_http_error(exc: BaseException) -> bool:
    """Retorna True apenas para erros HTTP transitórios (rede, 429, 5xx)

    Args:
        exc: exceção capturada pelo tenacity

    Returns:
        True se a exceção justifica nova tentativa
    """

    if isinstance(
        exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
    ):
        return True

    if isinstance(exc, requests.exceptions.HTTPError):
        if exc.response is None:
            return True
        status = exc.response.status_code
        return status == 429 or status >= 500

    return False


def _log_before_sleep(retry_state: RetryCallState) -> None:
    """Loga tentativa com contexto antes do sleep do backoff

    Args:
        retry_state: metadados da tentativa atual fornecidos pelo tenacity
    """

    exc = retry_state.outcome.exception()
    wait = getattr(retry_state.next_action, "sleep", 0)

    logger.warning(
        "http_retry_tentativa",
        tentativa=retry_state.attempt_number,
        erro=str(exc),
        aguardando_segundos=round(wait, 1),
    )


def http_retry(max_attempts: int = 3, min_wait: int = 2, max_wait: int = 30):
    """Decorator factory para chamadas HTTP externas com retry e backoff exponencial

    Retenta apenas erros transitórios (rede, 429, 5xx). Erros 4xx propagam imediatamente
    pois retry não resolve problemas de cliente

    Uso:
        @http_retry()
        def minha_chamada():
            response = requests.post(...)
            response.raise_for_status()
            return response.json()

    Args:
        max_attempts: número máximo de tentativas incluindo a primeira
        min_wait: espera mínima entre tentativas em segundos
        max_wait: espera máxima entre tentativas em segundos

    Returns:
        Decorador tenacity configurado
    """

    return retry(
        retry=retry_if_exception(_is_retryable_http_error),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=_log_before_sleep,
        reraise=True,
    )
