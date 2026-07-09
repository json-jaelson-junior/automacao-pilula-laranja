from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pilula_laranja.core.collect import RawItem
from pilula_laranja.core.extract import ExtractedItem, extract_all, extract_item


def _make_raw_item(url: str = "https://example.com/bitcoin-article") -> RawItem:
    """Cria um RawItem fake para uso nos testes."""
    return RawItem(
        source_name="Bitcoin Magazine",
        title="Bitcoin atinge novo recorde",
        url=url,
        published_at=datetime(2025, 7, 7, 10, 0, 0, tzinfo=UTC),
        summary="Resumo do artigo.",
    )


def _make_response(text: str, status_code: int = 200) -> MagicMock:
    """Cria um objeto Response fake do requests."""
    response = MagicMock()
    response.text = text
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    return response


def test_extract_item_com_trafilatura(mocker):
    """Caso feliz: trafilatura extrai conteúdo suficiente."""
    html = "<html><body><p>Conteúdo do artigo</p></body></html>"
    conteudo_extraido = "Conteúdo do artigo " * 20

    mocker.patch(
        "pilula_laranja.core.extract.requests.get",
        return_value=_make_response(html),
    )
    mocker.patch(
        "pilula_laranja.core.extract._extract_with_trafilatura",
        return_value=conteudo_extraido,
    )

    item = _make_raw_item()
    result = extract_item(item)

    assert result is not None
    assert isinstance(result, ExtractedItem)
    assert result.content == conteudo_extraido
    assert result.url == item.url
    assert result.source_name == item.source_name
    assert result.extracted_at is not None


def test_extract_item_fallback_readability(mocker):
    """Fallback: trafilatura falha, readability extrai o conteúdo."""
    html = "<html><body><p>Conteúdo do artigo</p></body></html>"
    conteudo_readability = "<​p>" + "Conteúdo via readability. " * 20 + "<​/p>"

    mocker.patch(
        "pilula_laranja.core.extract.requests.get",
        return_value=_make_response(html),
    )
    mocker.patch(
        "pilula_laranja.core.extract._extract_with_trafilatura",
        return_value=None,
    )
    mocker.patch(
        "pilula_laranja.core.extract._extract_with_readability",
        return_value=conteudo_readability,
    )

    item = _make_raw_item()
    result = extract_item(item)

    assert result is not None
    assert result.content == conteudo_readability


def test_extract_item_ambos_falham(mocker):
    """Erro: trafilatura e readability falham — retorna None sem quebrar."""
    html = "<html><body></body></html>"

    mocker.patch(
        "pilula_laranja.core.extract.requests.get",
        return_value=_make_response(html),
    )
    mocker.patch(
        "pilula_laranja.core.extract._extract_with_trafilatura",
        return_value=None,
    )
    mocker.patch(
        "pilula_laranja.core.extract._extract_with_readability",
        return_value=None,
    )

    result = extract_item(_make_raw_item())

    assert result is None


def test_extract_item_falha_http(mocker):
    """Erro: request HTTP falha — retorna None sem quebrar."""
    import requests as req

    mocker.patch(
        "pilula_laranja.core.extract.requests.get",
        side_effect=req.RequestException("timeout"),
    )

    result = extract_item(_make_raw_item())

    assert result is None


def test_extract_all_descarta_falhas(mocker):
    """extract_all descarta itens com falha e retorna só os válidos."""
    conteudo = "Conteúdo válido do artigo. " * 20

    item_valido = _make_raw_item("https://example.com/valido")
    item_invalido = _make_raw_item("https://example.com/invalido")

    def fake_extract(item: RawItem):
        if item.url == "https://example.com/valido":
            return ExtractedItem(
                source_name=item.source_name,
                title=item.title,
                url=item.url,
                published_at=item.published_at,
                summary=item.summary,
                content=conteudo,
                extracted_at=datetime.now(UTC),
            )
        return None

    mocker.patch(
        "pilula_laranja.core.extract.extract_item",
        side_effect=fake_extract,
    )

    result = extract_all([item_valido, item_invalido])

    assert len(result) == 1
    assert result[0].url == "https://example.com/valido"
