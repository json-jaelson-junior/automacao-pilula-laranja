from unittest.mock import MagicMock

import pytest

from pilula_laranja.clients.gemini import GeminiClient, GeminiQuotaError


@pytest.fixture
def mock_db() -> MagicMock:
    """Simula TursoClient com banco vazio por padrão."""
    db = MagicMock()
    db.execute.return_value = [{"total": None}]
    return db


@pytest.fixture
def mock_config() -> MagicMock:
    """Simula AppConfig com valores operacionais para os testes."""
    config = MagicMock()
    config.gemini.daily_token_limit = 1_000_000
    config.gemini.max_retries = 3
    config.gemini.timeout_seconds = 30
    return config


@pytest.fixture
def gemini_client(
    mock_db: MagicMock, mock_config: MagicMock, monkeypatch, mocker
) -> GeminiClient:
    """Instancia GeminiClient com API key fake e SDK mockado."""
    monkeypatch.setenv("GEMINI_API_KEY", "chave-fake-para-testes")
    mocker.patch("pilula_laranja.clients.gemini.genai.Client")
    return GeminiClient(db=mock_db, config=mock_config)


@pytest.fixture
def mock_response() -> MagicMock:
    """Simula GenerateContentResponse do SDK."""
    response = MagicMock()
    response.usage_metadata.total_token_count = 150
    response.text = "Resposta simulada do Gemini"
    return response


def test_init_raises_without_api_key(
    mock_db: MagicMock, mock_config: MagicMock, monkeypatch
) -> None:
    """Sem GEMINI_API_KEY, ValueError deve ser levantado no __init__."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY é obrigatória"):
        GeminiClient(db=mock_db, config=mock_config)


def test_generate_ok(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
    mock_response: MagicMock,
) -> None:
    """Caminho feliz: quota ok, API retorna, uso registrado, texto retornado."""
    gemini_client._client.models.generate_content.return_value = mock_response

    result = gemini_client.generate(
        prompt="Explique Bitcoin",
        model="gemini-2.0-flash",
        purpose="classify",
    )

    assert result == "Resposta simulada do Gemini"

    calls = mock_db.execute.call_args_list
    insert_call = calls[1]
    params = insert_call[0][1]

    assert params[0] == "gemini-2.0-flash"
    assert params[1] == "150"
    assert params[2] == "classify"


def test_generate_raises_quota_error_when_above_threshold(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
) -> None:
    """Uso >= 80% do limite deve levantar GeminiQuotaError."""
    mock_db.execute.return_value = [{"total": "850000"}]

    with pytest.raises(GeminiQuotaError, match="Quota acima de 80%"):
        gemini_client.generate(
            prompt="Explique Bitcoin",
            model="gemini-2.0-flash",
            purpose="classify",
        )


def test_generate_skips_api_when_quota_exceeded(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
) -> None:
    """Quando quota esgotada, generate_content nunca deve ser invocado."""
    mock_db.execute.return_value = [{"total": "900000"}]

    with pytest.raises(GeminiQuotaError):
        gemini_client.generate("prompt", "gemini-2.0-flash", "classify")

    gemini_client._client.models.generate_content.assert_not_called()


def test_generate_retries_on_transient_failure(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
    mock_response: MagicMock,
) -> None:
    """API falha 2x e sucede na 3ª tentativa — resultado deve ser retornado."""
    gemini_client._client.models.generate_content.side_effect = [
        Exception("timeout transitório"),
        Exception("503 Service Unavailable"),
        mock_response,
    ]

    result = gemini_client.generate("prompt", "gemini-2.0-flash", "classify")

    assert result == "Resposta simulada do Gemini"
    assert gemini_client._client.models.generate_content.call_count == 3


def test_generate_raises_after_max_retries(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
) -> None:
    """Todas as tentativas falhando deve repassar a exceção original."""
    gemini_client._client.models.generate_content.side_effect = Exception(
        "falha persistente na API"
    )

    with pytest.raises(Exception, match="falha persistente na API"):
        gemini_client.generate("prompt", "gemini-2.0-flash", "classify")

    assert gemini_client._client.models.generate_content.call_count == 3


def test_check_quota_ok_when_db_empty(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
) -> None:
    """Banco vazio (total=None) não deve levantar GeminiQuotaError."""
    mock_db.execute.return_value = [{"total": None}]

    gemini_client._check_quota("gemini-2.0-flash")


def test_record_usage_stores_tokens_as_string(
    gemini_client: GeminiClient,
    mock_db: MagicMock,
) -> None:
    """Tokens persistidos como str — schema tokens_used é TEXT."""
    gemini_client._record_usage(model="gemini-2.0-flash", tokens=500, purpose="rewrite")

    call_args = mock_db.execute.call_args[0]
    params = call_args[1]

    assert params[1] == "500"
    assert isinstance(params[1], str)
