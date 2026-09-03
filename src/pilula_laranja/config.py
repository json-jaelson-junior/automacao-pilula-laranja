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


class GeminiConfig(BaseModel):
    """Configurações operacionais do cliente Gemini"""

    daily_token_limit: int = 1_000_000  # Free tier Flash: 1M tokens/dia
    max_retries: int = 3
    timeout_seconds: int = 90
    classify_rpm: int = 15
    classify_rpd: int = 500
    rewrite_rpm: int = 5
    rewrite_rpd: int = 20


class AppConfig(BaseModel):
    sources: list[Source]
    keywords: Keywords
    blocklist: Blocklist
    gemini: GeminiConfig = GeminiConfig()


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
    gemini_data = _load_yaml("gemini.yaml")

    return AppConfig(
        sources=sources_data["sources"],
        keywords=keywords_data["keywords"],
        blocklist=blocklist_data["blocklist"],
        gemini=gemini_data["gemini"],
    )
