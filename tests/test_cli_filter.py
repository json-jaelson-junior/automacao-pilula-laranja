from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from pilula_laranja.cli import app
from pilula_laranja.clients.gemini import GeminiQuotaError
from pilula_laranja.core.extract import ExtractedItem
from pilula_laranja.db.connection import TursoError

runner = CliRunner()


def _make_item(url: str = "https://example.com/bitcoin") -> ExtractedItem:
    return ExtractedItem(
        source_name="Test Source",
        title="Bitcoin atinge nova alta histórica",
        url=url,
        published_at=datetime.now(UTC),
        summary="Resumo do artigo",
        content="Conteúdo completo do artigo sobre Bitcoin e blockchain",
        extracted_at=datetime.now(UTC),
    )


def test_filter_pipeline_completo() -> None:
    item = _make_item()

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso,
        patch("pilula_laranja.cli.collect_all", return_value=[MagicMock()]),
        patch("pilula_laranja.cli.extract_all", return_value=[item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[item]),
        patch("pilula_laranja.cli.filter_all", return_value=[item]),
        patch("pilula_laranja.cli.GeminiClient") as mock_gemini_cls,
        patch("pilula_laranja.cli.classify_all", return_value=[item]),
    ):
        mock_config.return_value = MagicMock()
        mock_turso.return_value = MagicMock()
        mock_gemini_cls.return_value = MagicMock()

        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 0
    assert "pipeline_concluido" in result.output


def test_filter_config_nao_encontrada() -> None:
    with patch(
        "pilula_laranja.cli.load_config", side_effect=FileNotFoundError("arquivo")
    ):
        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 1


def test_filter_turso_indisponivel() -> None:

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient", side_effect=TursoError("sem conexão")),
    ):
        mock_config.return_value = MagicMock()
        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 1


def test_filter_gemini_api_key_ausente() -> None:
    item = _make_item()

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso,
        patch("pilula_laranja.cli.collect_all", return_value=[MagicMock()]),
        patch("pilula_laranja.cli.extract_all", return_value=[item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[item]),
        patch("pilula_laranja.cli.filter_all", return_value=[item]),
        patch(
            "pilula_laranja.cli.GeminiClient", side_effect=ValueError("chave ausente")
        ),
    ):
        mock_config.return_value = MagicMock()
        mock_turso.return_value = MagicMock()

        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 1
    assert "gemini_api_key_ausente" in result.output


def test_filter_gemini_quota_esgotada() -> None:
    item = _make_item()

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso,
        patch("pilula_laranja.cli.collect_all", return_value=[MagicMock()]),
        patch("pilula_laranja.cli.extract_all", return_value=[item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[item]),
        patch("pilula_laranja.cli.filter_all", return_value=[item]),
        patch("pilula_laranja.cli.GeminiClient") as mock_gemini_cls,
        patch("pilula_laranja.cli.classify_all", side_effect=GeminiQuotaError("80%")),
    ):
        mock_config.return_value = MagicMock()
        mock_turso.return_value = MagicMock()
        mock_gemini_cls.return_value = MagicMock()

        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 1
    assert "gemini_quota_esgotada" in result.output


def test_filter_dry_run_sem_clientes_externos() -> None:
    item = _make_item()

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso_cls,
        patch("pilula_laranja.cli.GeminiClient") as mock_gemini_cls,
        patch("pilula_laranja.cli.collect_all", return_value=[MagicMock()]),
        patch("pilula_laranja.cli.extract_all", return_value=[item]),
        patch("pilula_laranja.cli.filter_new_items") as mock_dedup,
        patch("pilula_laranja.cli.filter_all", return_value=[item]),
        patch("pilula_laranja.cli.classify_all") as mock_classify,
    ):
        mock_config.return_value = MagicMock()

        result = runner.invoke(app, ["filter", "--dry-run"])

    assert result.exit_code == 0
    mock_turso_cls.assert_not_called()
    mock_gemini_cls.assert_not_called()
    mock_dedup.assert_not_called()
    mock_classify.assert_not_called()
    assert "pipeline_concluido" in result.output


def test_filter_coleta_sem_resultados() -> None:
    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso,
        patch("pilula_laranja.cli.collect_all", return_value=[]),
    ):
        mock_config.return_value = MagicMock()
        mock_turso.return_value = MagicMock()

        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 0
    assert "coleta_sem_resultados" in result.output


def test_filter_sem_itens_novos() -> None:
    item = _make_item()

    with (
        patch("pilula_laranja.cli.load_config") as mock_config,
        patch("pilula_laranja.cli.TursoClient") as mock_turso,
        patch("pilula_laranja.cli.collect_all", return_value=[MagicMock()]),
        patch("pilula_laranja.cli.extract_all", return_value=[item]),
        patch("pilula_laranja.cli.filter_new_items", return_value=[]),
    ):
        mock_config.return_value = MagicMock()
        mock_turso.return_value = MagicMock()

        result = runner.invoke(app, ["filter"])

    assert result.exit_code == 0
    assert "sem_itens_novos" in result.output
