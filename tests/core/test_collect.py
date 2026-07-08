from __future__ import annotations

from unittest.mock import MagicMock

from pilula_laranja.core.collect import RawItem, collect_all, fetch_feed


def _make_entry(
    title: str = "Bitcoin atinge novo recorde",
    link: str = "https://example.com/bitcoin-record",
    summary: str = "Resumo do artigo.",
    published: str | None = "Mon, 07 Jul 2025 10:00:00 +0000",
) -> MagicMock:
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": title,
        "link": link,
        "summary": summary,
        "published": published,
    }.get(key, default)
    return entry


def _make_parsed(entries: list, bozo: bool = False) -> MagicMock:
    parsed = MagicMock()
    parsed.entries = entries
    parsed.bozo = bozo
    parsed.bozo_exception = Exception("XML mal formado") if bozo else None
    return parsed


def test_fetch_feed_retorna_raw_item_valido(mocker):
    """Caso feliz: feed com uma entrada válida retorna RawItem correto."""
    entry = _make_entry()
    mocker.patch(
        "pilula_laranja.core.collect.feedparser.parse",
        return_value=_make_parsed([entry]),
    )

    result = fetch_feed("Bitcoin Magazine", "https://bitcoinmagazine.com/feed")

    assert len(result) == 1
    assert isinstance(result[0], RawItem)
    assert result[0].title == "Bitcoin atinge novo recorde"
    assert result[0].url == "https://example.com/bitcoin-record"
    assert result[0].source_name == "Bitcoin Magazine"
    assert result[0].published_at is not None


def test_fetch_feed_ignora_entry_sem_url(mocker):
    """Erro: entry sem link deve ser descartada silenciosamente."""
    entry = _make_entry(link="")
    mocker.patch(
        "pilula_laranja.core.collect.feedparser.parse",
        return_value=_make_parsed([entry]),
    )

    result = fetch_feed("Bitcoin Magazine", "https://bitcoinmagazine.com/feed")

    assert result == []


def test_fetch_feed_ignora_entry_sem_titulo(mocker):
    """Erro: entry sem título deve ser descartada silenciosamente."""
    entry = _make_entry(title="")
    mocker.patch(
        "pilula_laranja.core.collect.feedparser.parse",
        return_value=_make_parsed([entry]),
    )

    result = fetch_feed("Bitcoin Magazine", "https://bitcoinmagazine.com/feed")

    assert result == []


def test_fetch_feed_published_at_none_quando_data_ausente(mocker):
    """Edge case: entry sem data resulta em published_at=None, não em erro."""
    entry = _make_entry(published=None)
    mocker.patch(
        "pilula_laranja.core.collect.feedparser.parse",
        return_value=_make_parsed([entry]),
    )

    result = fetch_feed("Bitcoin Magazine", "https://bitcoinmagazine.com/feed")

    assert len(result) == 1
    assert result[0].published_at is None


def test_collect_all_ignora_fonte_inativa(mocker):
    """Feliz: fonte com active=False não deve ser coletada."""
    mock_fetch = mocker.patch("pilula_laranja.core.collect.fetch_feed")

    from pilula_laranja.config import AppConfig, Blocklist, Keywords, Source

    config = AppConfig(
        sources=[
            Source(
                name="Inativa",
                feed_url="https://example.com/feed",
                active=False,
            )
        ],
        keywords=Keywords(required=["bitcoin"], supporting=[]),
        blocklist=Blocklist(terms=[]),
    )

    result = collect_all(config)

    mock_fetch.assert_not_called()
    assert result == []
