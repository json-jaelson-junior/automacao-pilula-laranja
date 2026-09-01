from unittest.mock import MagicMock

import pytest

from pilula_laranja.clients.wordpress import PublishResult, WordPressClient
from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.core.publish import (
    _extract_title,
    _to_gutenberg_blocks,
    publish_all,
    publish_item,
)
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


def test_extract_title_retorna_titulo_e_body_sem_h2() -> None:
    html = "<h2>Bitcoin atinge recorde</h2><p>Conteúdo do artigo.</p>"
    title, body = _extract_title(html)
    assert title == "Bitcoin atinge recorde"
    assert "<h2>" not in body
    assert "<p>Conteúdo do artigo.</p>" in body


def test_extract_title_sem_h2_retorna_fallback() -> None:
    html = "<p>Sem título aqui.</p>"
    title, body = _extract_title(html)
    assert title == ""
    assert body == html


def test_extract_title_remove_tags_internas_do_h2() -> None:
    html = "<h2><strong>Bitcoin</strong> em alta</h2><p>Corpo.</p>"
    title, body = _extract_title(html)
    assert title == "Bitcoin em alta"


def test_extract_title_h2_com_atributos() -> None:
    html = '<h2 class="wp-title">Título com atributo</h2><p>Corpo.</p>'
    title, body = _extract_title(html)
    assert title == "Título com atributo"
    assert "<h2" not in body


def test_gutenberg_envolve_paragrafo() -> None:
    html = "<p>Texto simples.</p>"
    result = _to_gutenberg_blocks(html)
    assert "<!-- wp:paragraph -->" in result
    assert "<!-- /wp:paragraph -->" in result
    assert "<p>Texto simples.</p>" in result


def test_gutenberg_envolve_h2() -> None:
    html = "<h2>Título</h2>"
    result = _to_gutenberg_blocks(html)
    assert '<!-- wp:heading {"level":2} -->' in result
    assert "<!-- /wp:heading -->" in result


def test_gutenberg_envolve_lista() -> None:
    html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
    result = _to_gutenberg_blocks(html)
    assert "<!-- wp:list -->" in result
    assert "<!-- /wp:list -->" in result


def test_gutenberg_nao_altera_tags_nao_mapeadas() -> None:
    html = "<p>Texto com <span>span</span> interno.</p>"
    result = _to_gutenberg_blocks(html)
    assert "<span>span</span>" in result
