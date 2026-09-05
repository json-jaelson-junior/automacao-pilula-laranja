# Importações
from datetime import datetime

from pydantic import BaseModel


class ProcessedItem(BaseModel):
    """Representa uma linha da tabela processed_items, já validada e tipada."""

    id: int
    url_hash: str
    source_url: str
    title: str
    status: str
    created_at: datetime


class ApiUsage(BaseModel):
    """Representa uma linha da tabela api_usage, já validada e tipada."""

    id: int
    model: str
    tokens_used: int
    purpose: str
    created_at: datetime
