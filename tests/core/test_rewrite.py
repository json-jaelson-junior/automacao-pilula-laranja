from unittest.mock import MagicMock, patch

import pytest

from pilula_laranja.clients.gemini import GeminiQuotaError
from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.core.rewrite import (
    _parse_response,
    rewrite_all,
    rewrite_item,
)


@pytest.fixture
def sample_item() -> ExtractedItem:
    return ExtractedItem(
        title="Bitcoin hits new high",
        content="Bitcoin reached a new all-time high today...",
        url="https://example.com/article",
        source_name="CoinDesk",
        published_at="2025-01-01T00:00:00+00:00",
        summary="Summary here",
        extracted_at="2025-01-01T00:00:00+00:00",
    )


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


def test_parse_response_separa_excerpt_e_body():
    response = (
        "Resumo SEO aqui com palavras-chave\n---SEO---\n<h2>Título</h2><p>Corpo</p>"
    )
    excerpt, body = _parse_response(response)
    assert excerpt == "Resumo SEO aqui com palavras-chave"
    assert body == "<h2>Título</h2><p>Corpo</p>"


def test_parse_response_levanta_value_error_sem_separador():
    with pytest.raises(ValueError, match="---SEO---"):
        _parse_response("Resposta sem separador nenhuma")


def test_parse_response_maxsplit_preserva_separador_no_corpo():
    response = "Excerpt aqui\n---SEO---\n<p>Corpo com ---SEO--- no meio</p>"
    excerpt, body = _parse_response(response)
    assert excerpt == "Excerpt aqui"
    assert "---SEO--- no meio" in body


def test_rewrite_item_sucesso(sample_item, mock_client):
    mock_client.generate.return_value = (
        "Bitcoin bate recorde histórico\n---SEO---\n<h2>Título PT-BR</h2><p>Corpo</p>"
    )
    template = "{title}\n{content}\n{url}\n{source_name}"
    result = rewrite_item(sample_item, mock_client, template, "gemini-2.5-flash")
    assert result.success is True
    assert result.reason == "rewrite_ok"
    assert result.excerpt == "Bitcoin bate recorde histórico"
    assert "<h2>" in result.body
    assert result.item is sample_item


def test_rewrite_item_parse_error_retorna_failure(sample_item, mock_client):
    mock_client.generate.return_value = "Resposta sem separador"
    template = "{title}\n{content}\n{url}\n{source_name}"
    result = rewrite_item(sample_item, mock_client, template, "gemini-2.5-flash")
    assert result.success is False
    assert "rewrite_parse_error" in result.reason
    assert result.excerpt == ""
    assert result.body == ""


def test_rewrite_item_propaga_quota_error(sample_item, mock_client):
    mock_client.generate.side_effect = GeminiQuotaError("quota esgotada")
    template = "{title}\n{content}\n{url}\n{source_name}"
    with pytest.raises(GeminiQuotaError):
        rewrite_item(sample_item, mock_client, template, "gemini-2.5-flash")


def test_rewrite_all_retorna_apenas_sucessos(mock_client):
    item_ok = ExtractedItem(
        title="Good article",
        content="content",
        url="https://example.com/ok",
        source_name="CoinDesk",
        published_at="2025-01-01T00:00:00+00:00",
        summary="Summary ok",
        extracted_at="2025-01-01T00:00:00+00:00",
    )
    item_fail = ExtractedItem(
        title="Bad article",
        content="content",
        url="https://example.com/fail",
        source_name="Decrypt",
        published_at="2025-01-01T00:00:00+00:00",
        summary="Summary fail",
        extracted_at="2025-01-01T00:00:00+00:00",
    )
    mock_client.generate.side_effect = [
        "Excerpt ok\n---SEO---\n<h2>Título</h2><p>Corpo</p>",
        "Resposta sem separador",
    ]
    mock_config = MagicMock()
    mock_config.gemini.rewrite_rpm = 5
    mock_config.gemini.rewrite_rpd = 20

    with patch(
        "pilula_laranja.core.rewrite._load_prompt_template",
        return_value="{title}{content}{url}{source_name}",
    ):
        results = rewrite_all([item_ok, item_fail], mock_client, mock_config)
    assert len(results) == 1
    assert results[0].item.url == "https://example.com/ok"
