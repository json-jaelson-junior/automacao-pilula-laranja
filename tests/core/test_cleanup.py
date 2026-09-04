from unittest.mock import MagicMock

from pilula_laranja.core.cleanup import cleanup_api_usage, cleanup_processed_items

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_client(count: int) -> MagicMock:
    """TursoClient falso.

    O retorno de client.execute() para um SELECT COUNT(*) sempre vem como
    lista de dict com valores string (API HTTP do Turso) — replicamos isso
    aqui em vez de já entregar int, pra bater com o formato real.
    """
    client = MagicMock()
    client.execute.return_value = [{"total": str(count)}]
    return client


# ── cleanup_processed_items ───────────────────────────────────────────────────


def test_cleanup_processed_items_apaga_registros_antigos():
    # Happy path: existem 3 registros elegíveis, dry_run desligado → apaga
    client = _make_client(count=3)

    result = cleanup_processed_items(client, dry_run=False)

    assert result == 3
    # SELECT (contagem) + DELETE → duas chamadas em client.execute
    assert client.execute.call_count == 2


def test_cleanup_processed_items_dry_run_nao_apaga():
    # Edge case: dry_run=True → só conta, não deve chamar DELETE
    client = _make_client(count=5)

    result = cleanup_processed_items(client, dry_run=True)

    assert result == 5
    # Só o SELECT de contagem, DELETE nunca é chamado
    assert client.execute.call_count == 1


def test_cleanup_processed_items_sem_registros_nao_apaga():
    # Erro esperado (caso zero): nenhum registro elegível → não dispara DELETE
    client = _make_client(count=0)

    result = cleanup_processed_items(client, dry_run=False)

    assert result == 0
    assert client.execute.call_count == 1


# ── cleanup_api_usage ─────────────────────────────────────────────────────────


def test_cleanup_api_usage_apaga_registros_antigos():
    # Happy path: existem 10 registros elegíveis, dry_run desligado → apaga
    client = _make_client(count=10)

    result = cleanup_api_usage(client, dry_run=False)

    assert result == 10
    assert client.execute.call_count == 2


def test_cleanup_api_usage_dry_run_nao_apaga():
    # Edge case: dry_run=True → só conta, não apaga
    client = _make_client(count=7)

    result = cleanup_api_usage(client, dry_run=True)

    assert result == 7
    assert client.execute.call_count == 1
