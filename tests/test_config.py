# Importações

import pytest
from pydantic import ValidationError

from pilula_laranja.config import AppConfig, _load_yaml, load_config


# Bom: config válida carrega corretamente
def test_load_config_returns_app_config(tmp_path, monkeypatch):
    """load_config() deve retornar AppConfig válido com dados corretos."""
    monkeypatch.setattr("pilula_laranja.config.CONFIG_DIR", tmp_path)

    (tmp_path / "sources.yaml").write_text(
        "sources:\n"
        "  - name: Test Source\n"
        "    feed_url: https://example.com/feed\n"
        "    active: true\n"
    )

    (tmp_path / "keywords.yaml").write_text(
        "keywords:\n  required:\n    - bitcoin\n  supporting:\n    - lightining\n"
    )

    (tmp_path / "blocklist.yaml").write_text("blocklist:\n  terms:\n    - memecoin\n")

    (tmp_path / "gemini.yaml").write_text(
        "gemini:\n"
        "  daily_token_limit: 1000000\n"
        "  max_retries: 3\n"
        "  timeout_seconds: 30\n"
        "  classify_rpm: 15\n"
        "  classify_rpd: 500\n"
        "  rewrite_rpm: 5\n"
        "  rewrite_rpd: 20\n"
    )

    config = load_config()

    assert isinstance(config, AppConfig)
    assert len(config.sources) == 1
    assert config.sources[0].name == "Test Source"
    assert config.keywords.required == ["bitcoin"]
    assert config.blocklist.terms == ["memecoin"]


# Erro: URL inválida deve levantar ValidationError
def test_load_config_invalid_url_raises(tmp_path, monkeypatch):
    """Sources com feed_url inválida deve levantar ValidationError."""
    monkeypatch.setattr("pilula_laranja.config.CONFIG_DIR", tmp_path)

    (tmp_path / "sources.yaml").write_text(
        "sources:\n"
        "  - name: Bad Source\n"
        "    feed_url: nao-e-uma-url\n"
        "    active: true\n"
    )

    (tmp_path / "keywords.yaml").write_text(
        "keywords:\n  required:\n    - bitcoin\n  supporting: []\n"
    )

    (tmp_path / "blocklist.yaml").write_text("blocklist:\n  terms: []\n")

    (tmp_path / "gemini.yaml").write_text(
        "gemini:\n"
        "  daily_token_limit: 1000000\n"
        "  max_retries: 3\n"
        "  timeout_seconds: 30\n"
        "  classify_rpm: 15\n"
        "  classify_rpd: 500\n"
        "  rewrite_rpm: 5\n"
        "  rewrite_rpd: 20\n"
    )

    with pytest.raises(ValidationError):
        load_config()


# Edge case: arquivo inexistente deve levantar FileNotFoundError
def test_load_yaml_missing_file_raises(tmp_path, monkeypatch):
    """_load_yaml() deve levantar FileNotFoundError se o arquivo não existir."""
    monkeypatch.setattr("pilula_laranja.config.CONFIG_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        _load_yaml("nao_existe.yaml")
