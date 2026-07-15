from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pilula_laranja.cli import app

runner = CliRunner()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sources = [MagicMock(active=True, name="Bitcoin Magazine")]
    return config


@pytest.fixture
def mock_raw_items():
    return [MagicMock()]


@pytest.fixture
def mock_extracted_items():
    return [MagicMock()]


def test_collect_pipeline_completo(mock_config, mock_raw_items, mock_extracted_items):
    with (
        patch("pilula_laranja.cli.load_config", return_value=mock_config),
        patch("pilula_laranja.cli.TursoClient") as mock_turso_cls,
        patch("pilula_laranja.cli.collect_all", return_value=mock_raw_items),
        patch("pilula_laranja.cli.extract_all", return_value=mock_extracted_items),
        patch(
            "pilula_laranja.cli.filter_new_items", return_value=mock_extracted_items
        ) as mock_dedup,
    ):
        result = runner.invoke(app, ["collect"])

    assert result.exit_code == 0
    mock_turso_cls.assert_called_once()
    mock_dedup.assert_called_once()


def test_collect_dry_run_pula_banco(mock_config, mock_raw_items, mock_extracted_items):
    with (
        patch("pilula_laranja.cli.load_config", return_value=mock_config),
        patch("pilula_laranja.cli.TursoClient") as mock_turso_cls,
        patch("pilula_laranja.cli.collect_all", return_value=mock_raw_items),
        patch("pilula_laranja.cli.extract_all", return_value=mock_extracted_items),
        patch("pilula_laranja.cli.filter_new_items") as mock_dedup,
    ):
        result = runner.invoke(app, ["collect", "--dry-run"])

    assert result.exit_code == 0
    mock_turso_cls.assert_not_called()
    mock_dedup.assert_not_called()


def test_collect_falha_config_nao_encontrada():
    with patch(
        "pilula_laranja.cli.load_config",
        side_effect=FileNotFoundError("sources.yaml não encontrado"),
    ):
        result = runner.invoke(app, ["collect"])

    assert result.exit_code == 1


def test_collect_falha_turso_indisponivel(mock_config):
    from pilula_laranja.db.connection import TursoError

    with (
        patch("pilula_laranja.cli.load_config", return_value=mock_config),
        patch(
            "pilula_laranja.cli.TursoClient",
            side_effect=TursoError("credenciais ausentes"),
        ),
    ):
        result = runner.invoke(app, ["collect"])

    assert result.exit_code == 1


def test_collect_sem_itens_coletados(mock_config):
    with (
        patch("pilula_laranja.cli.load_config", return_value=mock_config),
        patch("pilula_laranja.cli.TursoClient"),
        patch("pilula_laranja.cli.collect_all", return_value=[]),
        patch("pilula_laranja.cli.extract_all") as mock_extract,
    ):
        result = runner.invoke(app, ["collect"])

    assert result.exit_code == 0
    mock_extract.assert_not_called()


def test_collect_sem_itens_extraidos(mock_config, mock_raw_items):
    with (
        patch("pilula_laranja.cli.load_config", return_value=mock_config),
        patch("pilula_laranja.cli.TursoClient"),
        patch("pilula_laranja.cli.collect_all", return_value=mock_raw_items),
        patch("pilula_laranja.cli.extract_all", return_value=[]),
        patch("pilula_laranja.cli.filter_new_items") as mock_dedup,
    ):
        result = runner.invoke(app, ["collect"])

    assert result.exit_code == 0
    mock_dedup.assert_not_called()
