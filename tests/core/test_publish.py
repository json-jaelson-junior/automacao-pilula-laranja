from unittest.mock import MagicMock

import pytest

from pilula_laranja.clients.wordpress import PublishResult, WordPressClient
from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.core.publish import publish_all, publish_item
from pilula_laranja.core.rewrite import RewriteResult


@pytest.fixture
def extracted_item() -> ExtractedItem:
    return ExtractedItem(
        title="Bitcoin atinge novo recorde",
        content="Conteúdo original do artigo.",
        url="https://bitcoinmagazine.com/artigo",
        source_name="Bitcoin Magazine",
        published_at="2025-01-01T00:00:00",
        summary="Resumo do artigo.",
        extracted_at="2025-01-01T00:00:00",
        sha256="abc123",
    )


@pytest.fixture
def rewrite_result(extracted_item) -> RewriteResult:
    return RewriteResult(
        item=extracted_item,
        excerpt="Bitcoin bate recorde histórico segundo analistas do mercado.",
        body="<​p>" + "Bitcoin atinge novo recorde histórico. " * 10 + "<​/p>",
        success=True,
        reason="rewrite_ok",
    )


@pytest.fixture
def mock_wp_client() -> MagicMock:
    client = MagicMock(spec=WordPressClient)
    client.create_draft.return_value = PublishResult(
        post_id=42,
        post_url="https://pilulalaranja.com/noticias/bitcoin-atinge-novo-recorde/",
        success=True,
        reason="publish_ok",
    )
    return client


def test_publish_item_sucesso(rewrite_result, mock_wp_client):
    result = publish_item(rewrite_result, mock_wp_client)

    assert result.success is True
    assert result.post_id == 42
    assert result.reason == "publish_ok"
    mock_wp_client.create_draft.assert_called_once()


def test_publish_item_sanitizacao_falha(rewrite_result, mock_wp_client):
    rewrite_result.body = ""

    result = publish_item(rewrite_result, mock_wp_client)

    assert result.success is False
    assert "sanitization_error" in result.reason
    mock_wp_client.create_draft.assert_not_called()


def test_publish_all_agrega_resultados(rewrite_result, mock_wp_client):
    failed_result = RewriteResult(
        item=rewrite_result.item,
        excerpt="",
        body="",
        success=True,
        reason="rewrite_ok",
    )

    results = publish_all([rewrite_result, failed_result], mock_wp_client)

    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False
