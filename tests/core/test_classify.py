from datetime import UTC, datetime

import pytest

from pilula_laranja.clients.gemini import GeminiQuotaError
from pilula_laranja.core.classify import (
    _build_prompt,
    _parse_response,
    classify_all,
    classify_item,
)
from pilula_laranja.core.extract import ExtractedItem

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_item(url: str = "https://bitcoinmagazine.com/article-1") -> ExtractedItem:
    """Fábrica de ExtractedItem com todos os campos obrigatórios preenchidos.

    Centraliza a construção — se ExtractedItem ganhar novos campos,
    corrigimos só aqui e todos os testes continuam funcionando.
    """
    return ExtractedItem(
        url=url,
        title="Bitcoin atinge novo recorde institucional",
        content="Grandes bancos americanos aumentaram exposição ao Bitcoin em 2025.",
        summary="Bancos aumentam exposição ao Bitcoin.",
        source_name="Bitcoin Magazine",
        published_at=None,
        extracted_at=datetime.now(UTC),
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def item() -> ExtractedItem:
    return _make_item()


@pytest.fixture()
def template() -> str:
    return "Título: {title}\nConteúdo: {content}\nSIM ou NÃO?"


# ─── Testes de _parse_response ────────────────────────────────────────────────


def test_parse_response_sim_exato() -> None:
    assert _parse_response("SIM") is True


def test_parse_response_nao_exato() -> None:
    assert _parse_response("NÃO") is False


def test_parse_response_sim_com_whitespace() -> None:
    assert _parse_response("  SIM\n") is True


def test_parse_response_sim_lowercase() -> None:
    assert _parse_response("sim") is True


def test_parse_response_sim_com_pontuacao() -> None:
    assert _parse_response("SIM.") is True


def test_parse_response_resposta_inesperada() -> None:
    assert _parse_response("Talvez seja relevante") is False


# ─── Testes de _build_prompt ──────────────────────────────────────────────────


def test_build_prompt_substitui_placeholders(
    item: ExtractedItem, template: str
) -> None:
    prompt = _build_prompt(template, item)
    assert item.title in prompt
    assert "Grandes bancos" in prompt


def test_build_prompt_trunca_conteudo_longo(template: str) -> None:
    item_longo = ExtractedItem(
        url="https://example.com",
        title="Título",
        content="x" * 5000,
        summary="resumo",
        source_name="Fonte",
        published_at=None,
        extracted_at=datetime.now(UTC),
    )
    prompt = _build_prompt(template, item_longo)
    assert "x" * 3001 not in prompt
    assert "x" * 3000 in prompt


# ─── Testes de classify_item ─────────────────────────────────────────────────


def test_classify_item_aprovado(
    item: ExtractedItem, template: str, mocker: pytest.fixture
) -> None:
    mock_client = mocker.MagicMock()
    mock_client.generate.return_value = "SIM"

    result = classify_item(item, mock_client, template, "gemini-2.5-flash")

    assert result.passed is True
    assert result.reason == "semantic_approved"
    mock_client.generate.assert_called_once_with(
        prompt=mocker.ANY,
        model="gemini-2.5-flash",
        purpose="classify",
    )


def test_classify_item_rejeitado(
    item: ExtractedItem, template: str, mocker: pytest.fixture
) -> None:
    mock_client = mocker.MagicMock()
    mock_client.generate.return_value = "NÃO"

    result = classify_item(item, mock_client, template, "gemini-2.5-flash")

    assert result.passed is False
    assert result.reason == "semantic_rejected"


def test_classify_item_falha_generica_nao_para_batch(
    item: ExtractedItem, template: str, mocker: pytest.fixture
) -> None:
    mock_client = mocker.MagicMock()
    mock_client.generate.side_effect = ConnectionError("timeout após 3 tentativas")

    result = classify_item(item, mock_client, template, "gemini-2.5-flash")

    assert result.passed is False
    assert "classify_error" in result.reason
    assert "timeout" in result.reason


def test_classify_item_quota_error_propaga(
    item: ExtractedItem, template: str, mocker: pytest.fixture
) -> None:
    mock_client = mocker.MagicMock()
    mock_client.generate.side_effect = GeminiQuotaError("80% atingido")

    with pytest.raises(GeminiQuotaError):
        classify_item(item, mock_client, template, "gemini-2.5-flash")


# ─── Testes de classify_all ───────────────────────────────────────────────────


def test_classify_all_retorna_apenas_aprovados(mocker: pytest.fixture) -> None:
    items = [_make_item(url=f"https://example.com/{i}") for i in range(3)]

    mock_client = mocker.MagicMock()
    mock_client.generate.side_effect = ["SIM", "NÃO", "SIM"]

    mocker.patch(
        "pilula_laranja.core.classify._load_prompt_template",
        return_value="Título: {title}\nConteúdo: {content}",
    )

    result = classify_all(items, mock_client, mocker.MagicMock())

    assert len(result) == 2
    assert result[0].url == "https://example.com/0"
    assert result[1].url == "https://example.com/2"


def test_classify_all_propaga_quota_error(mocker: pytest.fixture) -> None:
    items = [_make_item(url=f"https://example.com/{i}") for i in range(2)]

    mock_client = mocker.MagicMock()
    mock_client.generate.side_effect = GeminiQuotaError("quota diária atingida")

    mocker.patch(
        "pilula_laranja.core.classify._load_prompt_template",
        return_value="Título: {title}\nConteúdo: {content}",
    )

    with pytest.raises(GeminiQuotaError):
        classify_all(items, mock_client, mocker.MagicMock())


def test_classify_all_lista_vazia(mocker: pytest.fixture) -> None:
    mock_client = mocker.MagicMock()
    mocker.patch(
        "pilula_laranja.core.classify._load_prompt_template",
        return_value="Título: {title}\nConteúdo: {content}",
    )

    result = classify_all([], mock_client, mocker.MagicMock())

    assert result == []
    mock_client.generate.assert_not_called()
