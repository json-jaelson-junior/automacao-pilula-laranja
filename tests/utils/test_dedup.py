from datetime import UTC, datetime

import pytest

from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.db.connection import TursoError
from pilula_laranja.utils.dedup import (
    compute_hash,
    filter_new_items,
    is_duplicate,
    mark_processed,
)


@pytest.fixture
def sample_item():
    return ExtractedItem(
        source_name="Bitcoin Magazine",
        title="Bitcoin atinge novo recorde",
        url="https://bitcoinmagazine.com/article/123",
        published_at=datetime.now(UTC),
        summary="Resumo do artigo.",
        content="Conteúdo completo do artigo.",
        extracted_at=datetime.now(UTC),
    )


# Teste 1 — compute_hash é determinístico
def test_compute_hash_deterministico():
    url = "https://bitcoinmagazine.com/article/123"
    assert compute_hash(url) == compute_hash(url)
    assert len(compute_hash(url)) == 64


# Teste 2 — is_duplicate retorna False quando o banco não encontra o hash
def test_is_duplicate_retorna_false_para_item_novo(mocker):
    mock_client = mocker.MagicMock()
    mock_client.execute.return_value = []

    result = is_duplicate(mock_client, "hash_qualquer")

    assert result is False
    mock_client.execute.assert_called_once()


# Teste 3 — is_duplicate retorna True quando o banco encontra o hash
def test_is_duplicate_retorna_true_para_duplicado(mocker):
    mock_client = mocker.MagicMock()
    mock_client.execute.return_value = [{"1": "1"}]

    result = is_duplicate(mock_client, "hash_qualquer")

    assert result is True


# Teste 4 — filter_new_items: novos passam, duplicado é descartado
def test_filter_new_items_descarta_duplicados(mocker, sample_item):
    mock_client = mocker.MagicMock()

    item_novo = sample_item.model_copy(
        update={"url": "https://bitcoinmagazine.com/article/999"}
    )

    mocker.patch(
        "pilula_laranja.utils.dedup.is_duplicate",
        side_effect=[True, False],
    )
    mocker.patch("pilula_laranja.utils.dedup.mark_processed")

    result = filter_new_items(mock_client, [sample_item, item_novo])

    assert len(result) == 1
    assert result[0].url == item_novo.url


# Teste 5 — mark_processed: erro do banco é propagado como TursoError
def test_mark_processed_propaga_turso_error(mocker, sample_item):
    mock_client = mocker.MagicMock()
    mock_client.execute.side_effect = TursoError("falha de conexão")

    with pytest.raises(TursoError):
        mark_processed(mock_client, sample_item, "hash_qualquer")
