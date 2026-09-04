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


def test_publish_dry_run_sem_wp():
    mock_item = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True

    with (
        patch("pilula_laranja.cli.load_config"),
        patch("pilula_laranja.cli.collect_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.extract_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.GeminiClient"),
        patch("pilula_laranja.cli.classify_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.rewrite_all", return_value=[mock_result]),
        patch("pilula_laranja.cli.WordPressClient") as mock_wp,
    ):
        result = runner.invoke(app, ["publish", "--dry-run"])

    assert result.exit_code == 0
    mock_wp.assert_not_called()


def test_publish_chama_wp_sem_dry_run():
    mock_item = MagicMock()
    mock_rewrite = MagicMock()
    mock_rewrite.success = True
    mock_publish = MagicMock()
    mock_publish.success = True

    with (
        patch("pilula_laranja.cli.load_config"),
        patch("pilula_laranja.cli.TursoClient"),
        patch("pilula_laranja.cli.collect_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.extract_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.GeminiClient"),
        patch("pilula_laranja.cli.classify_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.rewrite_all", return_value=[mock_rewrite]),
        patch("pilula_laranja.cli.WordPressClient"),
        patch(
            "pilula_laranja.cli.publish_all", return_value=[mock_publish]
        ) as mock_pub,
    ):
        result = runner.invoke(app, ["publish"])

    assert result.exit_code == 0
    mock_pub.assert_called_once()


def test_publish_quota_error_reescrita():
    from pilula_laranja.clients.gemini import GeminiQuotaError

    mock_item = MagicMock()

    with (
        patch("pilula_laranja.cli.load_config"),
        patch("pilula_laranja.cli.TursoClient"),
        patch("pilula_laranja.cli.collect_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.extract_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[mock_item]),
        patch("pilula_laranja.cli.filter_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.GeminiClient"),
        patch("pilula_laranja.cli.classify_all", return_value=[mock_item]),
        patch("pilula_laranja.cli.rewrite_all", side_effect=GeminiQuotaError("quota")),
    ):
        result = runner.invoke(app, ["publish"])

    assert result.exit_code == 1


def test_cleanup_pipeline_completo():
    # Happy path: as duas tabelas retornam contagem > 0, dry_run desligado
    with (
        patch("pilula_laranja.cli.TursoClient"),
        patch(
            "pilula_laranja.cli.cleanup_processed_items", return_value=3
        ) as mock_processed,
        patch("pilula_laranja.cli.cleanup_api_usage", return_value=7) as mock_api_usage,
    ):
        result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 0
    mock_processed.assert_called_once()
    mock_api_usage.assert_called_once()


def test_cleanup_dry_run_nao_apaga():
    # Edge case: --dry-run é repassado para as duas funções
    with (
        patch("pilula_laranja.cli.TursoClient"),
        patch(
            "pilula_laranja.cli.cleanup_processed_items", return_value=5
        ) as mock_processed,
        patch("pilula_laranja.cli.cleanup_api_usage", return_value=2) as mock_api_usage,
    ):
        result = runner.invoke(app, ["cleanup", "--dry-run"])

    assert result.exit_code == 0
    # kwargs dry_run=True chegou em ambas as chamadas
    assert mock_processed.call_args.kwargs["dry_run"] is True
    assert mock_api_usage.call_args.kwargs["dry_run"] is True


def test_cleanup_falha_turso_indisponivel():
    from pilula_laranja.db.connection import TursoError

    with patch(
        "pilula_laranja.cli.TursoClient",
        side_effect=TursoError("credenciais ausentes"),
    ):
        result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 1


def test_cleanup_falha_isolada_processed_items():
    # Erro esperado: processed_items falha, mas api_usage ainda deve rodar
    from pilula_laranja.db.connection import TursoError

    with (
        patch("pilula_laranja.cli.TursoClient"),
        patch(
            "pilula_laranja.cli.cleanup_processed_items",
            side_effect=TursoError("timeout"),
        ),
        patch("pilula_laranja.cli.cleanup_api_usage", return_value=4) as mock_api_usage,
    ):
        result = runner.invoke(app, ["cleanup"])

    # Exit code 1 porque houve falha, MAS api_usage foi chamado mesmo assim
    assert result.exit_code == 1
    mock_api_usage.assert_called_once()


def test_cleanup_falha_isolada_api_usage():
    # Erro esperado: api_usage falha, mas processed_items já rodou antes
    from pilula_laranja.db.connection import TursoError

    with (
        patch("pilula_laranja.cli.TursoClient"),
        patch(
            "pilula_laranja.cli.cleanup_processed_items", return_value=6
        ) as mock_processed,
        patch(
            "pilula_laranja.cli.cleanup_api_usage",
            side_effect=TursoError("timeout"),
        ),
    ):
        result = runner.invoke(app, ["cleanup"])

    assert result.exit_code == 1
    mock_processed.assert_called_once()
