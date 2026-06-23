# Importações

from unittest.mock import MagicMock, patch

import pytest

from pilula_laranja.db.connection import TursoClient, TursoError


# Fixture: cria um TursoClient com variáveis de ambiente falsas
@pytest.fixture
def client(monkeypatch):
    """Cria TursoClient com credenciais fake para testes."""
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://fake-db.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "fake-token")
    return TursoClient()


def make_ok_response(cols: list[str], rows: list[list]) -> dict:
    """Monta um payload de resposta bem-sucedida no formato da API do Turso."""
    return {
        "results": [
            {
                "type": "ok",
                "response": {
                    "result": {
                        "cols": [{"name": c} for c in cols],
                        "rows": [[{"value": str(v)} for v in row] for row in rows],
                    }
                },
            }
        ]
    }


def test_execute_retorna_linhas(client):
    """Caso feliz: execute() retorna lista de dicts corretamente."""
    fake_response = make_ok_response(
        cols=["id", "url_hash"],
        rows=[["1", "abc123"], ["2", "def456"]],
    )

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = fake_response

    with patch.object(client._session, "post", return_value=mock_resp):
        result = client.execute("SELECT id, url_hash FROM processed_items")

    assert result == [
        {"id": "1", "url_hash": "abc123"},
        {"id": "2", "url_hash": "def456"},
    ]


def test_execute_erro_http(client):
    """Erro HTTP: raise_for_status lança exceção → TursoError."""
    import requests

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.RequestException(
        "500 Server Error"
    )

    with (
        patch.object(client._session, "post", return_value=mock_resp),
        pytest.raises(TursoError, match="Falha na comunicação"),
    ):
        client.execute("SELECT 1")


def test_execute_erro_no_json(client):
    """HTTP 200 mas API retorna erro dentro do JSON → TursoError."""
    fake_response = {
        "results": [
            {
                "type": "error",
                "error": {"message": "table not found"},
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = fake_response

    with (
        patch.object(client._session, "post", return_value=mock_resp),
        pytest.raises(TursoError, match="table not found"),
    ):
        client.execute("SELECT * FROM tabela_inexistente")
