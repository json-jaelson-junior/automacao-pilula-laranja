from unittest.mock import MagicMock, patch

import pytest

from pilula_laranja.clients.gemini import GeminiQuotaError
from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.core.rewrite import (
    _interleave_by_source,
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


def _make_item(source_name: str, url: str) -> ExtractedItem:
    """Helper para reduzir repetição na criação de ExtractedItem nos testes
    de intercalação — só source_name e url variam, o resto é irrelevante
    para essa lógica."""
    return ExtractedItem(
        title="Título qualquer",
        content="Conteúdo qualquer",
        url=url,
        source_name=source_name,
        published_at="2025-01-01T00:00:00+00:00",
        summary="Resumo qualquer",
        extracted_at="2025-01-01T00:00:00+00:00",
    )


def test_interleave_by_source_alterna_fontes_igualmente():
    """3 fontes com 2 itens cada devem sair intercaladas: A, B, C, A, B, C"""
    items = [
        _make_item("A", "https://a.com/1"),
        _make_item("A", "https://a.com/2"),
        _make_item("B", "https://b.com/1"),
        _make_item("B", "https://b.com/2"),
        _make_item("C", "https://c.com/1"),
        _make_item("C", "https://c.com/2"),
    ]
    result = _interleave_by_source(items)
    sources_in_order = [item.source_name for item in result]
    assert sources_in_order == ["A", "B", "C", "A", "B", "C"]


def test_interleave_by_source_fonte_maior_nao_perde_itens():
    """Reproduz o cenário real: 13 itens (fonte com mais itens que as
    outras). Nenhum item pode ser descartado pela função — o corte por
    max_items acontece depois, fora dela."""
    items = (
        [_make_item("Decrypt", f"https://decrypt.com/{i}") for i in range(5)]
        + [_make_item("CoinDesk", f"https://coindesk.com/{i}") for i in range(5)]
        + [_make_item("Bitcoin Magazine", f"https://btcmag.com/{i}") for i in range(3)]
    )
    result = _interleave_by_source(items)
    assert len(result) == 13
    assert {item.url for item in result} == {item.url for item in items}


def test_interleave_by_source_preserva_ordem_dentro_da_fonte():
    """Dentro de uma mesma fonte, a ordem original de chegada não pode
    ser embaralhada — só a alternância ENTRE fontes é round-robin."""
    items = [
        _make_item("A", "https://a.com/1"),
        _make_item("B", "https://b.com/1"),
        _make_item("A", "https://a.com/2"),
    ]
    result = _interleave_by_source(items)
    a_urls_in_order = [item.url for item in result if item.source_name == "A"]
    assert a_urls_in_order == ["https://a.com/1", "https://a.com/2"]


def test_interleave_by_source_lista_vazia_retorna_vazia():
    assert _interleave_by_source([]) == []


def test_rewrite_all_aplica_max_items_rpd_dividido_por_dois(mock_client):
    """Confirma que o corte usa rpd // 2 (2 runs/dia por modelo), não
    mais o // 5 antigo. Com rpd=20, max_items deve ser 10 — então de 12
    itens, só 10 devem ser processados (10 chamadas ao Gemini)."""
    items = [_make_item("CoinDesk", f"https://coindesk.com/{i}") for i in range(12)]
    mock_client.generate.return_value = "Excerpt\n---SEO---\n<p>Corpo</p>"
    mock_config = MagicMock()
    mock_config.gemini.rewrite_rpm = 300
    mock_config.gemini.rewrite_rpd = 20

    with patch(
        "pilula_laranja.core.rewrite._load_prompt_template",
        return_value="{title}{content}{url}{source_name}",
    ):
        results = rewrite_all(items, mock_client, mock_config)

    assert mock_client.generate.call_count == 10
    assert len(results) == 10
