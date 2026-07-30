from unittest.mock import MagicMock, patch

import pytest
import requests as req

from pilula_laranja.clients.wordpress import DraftPost, WordPressClient


@pytest.fixture
def draft_post() -> DraftPost:
    return DraftPost(
        title="Bitcoin atinge novo recorde",
        content=(
            "<p>Conteúdo sanitizado.</p><!-- PILULA_LARANJA: {} -->"
            "\n<p>Fonte: Bitcoin atinge novo recorde</p>"
        ),
        excerpt="Bitcoin atinge novo recorde histórico segundo analistas.",
    )


@pytest.fixture
def wp_client(monkeypatch) -> WordPressClient:
    monkeypatch.setenv("WP_URL", "https://pilulalaranja.com")
    monkeypatch.setenv("WP_USERNAME", "automacao")
    monkeypatch.setenv("WP_APP_PASSWORD", "xxxx xxxx xxxx xxxx xxxx xxxx")
    return WordPressClient()


def test_create_draft_sucesso(wp_client, draft_post):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 42,
        "link": "https://pilulalaranja.com/noticias/bitcoin-atinge-novo-recorde/",
    }

    with patch.object(wp_client._session, "post", return_value=mock_response):
        result = wp_client.create_draft(draft_post)

    assert result.success is True
    assert result.post_id == 42
    assert (
        result.post_url
        == "https://pilulalaranja.com/noticias/bitcoin-atinge-novo-recorde/"
    )
    assert result.reason == "publish_ok"


def test_create_draft_erro_401(wp_client, draft_post):
    mock_response = MagicMock()
    mock_response.status_code = 401
    http_error = req.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error

    with patch.object(wp_client._session, "post", return_value=mock_response):
        result = wp_client.create_draft(draft_post)

    assert result.success is False
    assert result.post_id == 0
    assert result.post_url == ""
    assert "publish_error" in result.reason


def test_create_draft_status_sempre_draft(wp_client, draft_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 7,
        "link": "https://pilulalaranja.com/noticias/bitcoin-atinge-novo-recorde/",
    }

    with patch.object(
        wp_client._session, "post", return_value=mock_response
    ) as mock_post:
        wp_client.create_draft(draft_post)

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["status"] == "draft"
