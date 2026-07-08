# Importações
from pathlib import Path

import yaml
from pydantic import BaseModel, HttpUrl

# Modelos


class Source(BaseModel):
    name: str
    feed_url: HttpUrl
    active: bool = True


class Keywords(BaseModel):
    required: list[str]
    supporting: list[str]


class Blocklist(BaseModel):
    terms: list[str]


class AppConfig(BaseModel):
    sources: list[Source]
    keywords: Keywords
    blocklist: Blocklist


# Loader

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_yaml(filename: str) -> dict:
    """Lê um arquivo YAML do diretório config/ e retorna um dicionário"""
    path = CONFIG_DIR / filename
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> AppConfig:
    """Carrega e valida todas as configurações do projeto

    Return:
        AppConfig: objeto validade com sources, keywords e blocklist

    Raises:
    ValidationError: se algum YAML estiver mal formado ou com campos faltando
    FileNotFoundError: se algum arquivo de config não existir
    """
    sources_data = _load_yaml("sources.yaml")
    keywords_data = _load_yaml("keywords.yaml")
    blocklist_data = _load_yaml("blocklist.yaml")

    return AppConfig(
        sources=sources_data["sources"],
        keywords=keywords_data["keywords"],
        blocklist=blocklist_data["blocklist"],
    )
