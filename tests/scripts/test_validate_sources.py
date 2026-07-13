from unittest.mock import MagicMock

import pytest
import requests

from scripts.validate_sources import validate_all, validate_source


@pytest.fixture
def mock_config():
    config = MagicMock()

    source1 = MagicMock()
    source1.name = "Bitcoin Magazine"
    source1.feed_url = "https://bitcoinmagazine.com/feed"
    source1.enabled = True

    source2 = MagicMock()
    source2.name = "CoinDesk"
    source2.feed_url = "https://coindesk.com/feed"
    source2.enabled = True

    config.sources = [source1, source2]
    return config


def test_validate_source_retorna_true_para_feed_valido(mocker):
    mock_response = MagicMock()
    rss_xml = "<rss><channel><item><title>Test</title></item></channel></rss>"
    mock_response.text = rss_xml
    mock_response.raise_for_status.return_value = None
    mocker.patch("scripts.validate_sources.requests.get", return_value=mock_response)

    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [MagicMock()]
    mocker.patch("scripts.validate_sources.feedparser.parse", return_value=mock_feed)

    success, message = validate_source(
        "Bitcoin Magazine", "https://bitcoinmagazine.com/feed"
    )

    assert success is True
    assert "OK" in message


def test_validate_source_retorna_false_em_timeout(mocker):
    mocker.patch(
        "scripts.validate_sources.requests.get",
        side_effect=requests.exceptions.Timeout,
    )

    success, message = validate_source(
        "Bitcoin Magazine", "https://bitcoinmagazine.com/feed"
    )

    assert success is False
    assert "timeout" in message


def test_validate_source_retorna_false_para_xml_malformado(mocker):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mocker.patch("scripts.validate_sources.requests.get", return_value=mock_response)

    mock_feed = MagicMock()
    mock_feed.bozo = True
    mock_feed.bozo_exception = Exception("XML syntax error")
    mocker.patch("scripts.validate_sources.feedparser.parse", return_value=mock_feed)

    success, message = validate_source(
        "Bitcoin Magazine", "https://bitcoinmagazine.com/feed"
    )

    assert success is False
    assert "malformado" in message


def test_validate_all_retorna_true_quando_tudo_passa(mocker, mock_config):
    mocker.patch(
        "scripts.validate_sources.validate_source",
        return_value=(True, "OK"),
    )

    result = validate_all(mock_config)

    assert result is True


def test_validate_all_retorna_false_quando_fonte_falha(mocker, mock_config):
    mocker.patch(
        "scripts.validate_sources.validate_source",
        side_effect=[(True, "OK"), (False, "timeout")],
    )

    result = validate_all(mock_config)

    assert result is False
