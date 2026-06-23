# Importações

from unittest.mock import MagicMock

import pytest

from pilula_laranja.db.connection import TursoError
from pilula_laranja.db.migrations import run_migrations


@pytest.fixture
def mock_client():
    """Cliente Turso mockado — não faz chamadas reais."""
    return MagicMock()


def test_migrations_executam_duas_tabelas(mock_client):
    """Caso feliz: run_migrations chama execute duas vezes."""
    mock_client.execute.return_value = []

    run_migrations(mock_client)

    assert mock_client.execute.call_count == 2


def test_migrations_sao_idempotentes(mock_client):
    """Rodar duas vezes não deve lançar exceção."""
    mock_client.execute.return_value = []

    run_migrations(mock_client)
    run_migrations(mock_client)

    assert mock_client.execute.call_count == 4


def test_migrations_propagam_erro(mock_client):
    """Se execute lançar TursoError, run_migrations deve propagar."""
    mock_client.execute.side_effect = TursoError("falha simulada")

    with pytest.raises(TursoError, match="falha simulada"):
        run_migrations(mock_client)
