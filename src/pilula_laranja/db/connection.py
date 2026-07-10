# Importações
import os
from typing import Any

import requests


class TursoError(Exception):
    """Erro genérico de comunicação com Turso"""

    pass


class TursoClient:
    """Cliente HTTP para a API do Turso (libSQL over HTTP)"""

    def __init__(self) -> None:
        url = os.environ.get("TURSO_DATABASE_URL", "")
        token = os.environ.get("TURSO_AUTH_TOKEN", "")

        if not url or not token:
            raise TursoError("TURSO_DATABASE_URL e TURSO_AUTH_TOKEN são obrigatórios")

        # Normaliza o schema: libsql:// para https://
        self._base_url = url.replace("libsql://", "https://") + "/v2/pipeline"

        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def execute(self, sql: str, params: list[Any] | None = None) -> list[dict]:
        """Executa uma query SQL e retorna as linhas como lista de dicts"""

        stmt = self._build_stmt(sql, params)
        return self._send([{"type": "execute", "stmt": stmt}])

    def executemany(self, sql: str, list_of_params: list[list[Any]]) -> None:
        """Executa a mesma query SQL para múltiplos conjuntos de parâmetros"""

        requests_payload = [
            {"type": "execute", "stmt": self._build_stmt(sql, params)}
            for params in list_of_params
        ]
        self._send(requests_payload)

    def _build_stmt(self, sql: str, params: list[Any] | None) -> dict:
        """Monta o objeto stmt esperado pela API do Turso"""

        stmt: dict[str, Any] = {"sql": sql, "args": []}
        if params:
            stmt["args"] = [self._encode_value(p) for p in params]
        return stmt

    def _encode_value(self, value: Any) -> dict:
        """Converte valor Python para o formato tipado da API do Turso"""

        if value is None:
            return {"type": "null", "value": None}
        if isinstance(value, bool):
            return {"type": "integer", "value": str(int(value))}
        if isinstance(value, int):
            return {"type": "integer", "value": str(value)}
        if isinstance(value, float):
            return {"type": "float", "value": str(value)}
        return {"type": "text", "value": str(value)}

    def _send(self, requests_payload: list[dict]) -> list[dict]:
        """Envia o payload para a API e retorna as linhas da última query"""

        try:
            response = self._session.post(
                self._base_url,
                json={"requests": requests_payload},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise TursoError(f"Falha na comunicação com o Turso: {e}") from e

        data = response.json()

        # Verifica error retornados dentro do JSON da API
        for result in data.get("results", []):
            if result.get("type") == "error":
                raise TursoError(f"Erro do Turso: {result['error']['message']}")

        # Extrai linhas da última query executada
        last = data["results"][-1]
        if last["type"] != "ok":
            return []

        rows_data = last["response"]["result"]
        cols = [c["name"] for c in rows_data["cols"]]
        return [
            dict(zip(cols, [v["value"] for v in row], strict=False))
            for row in rows_data["rows"]
        ]
