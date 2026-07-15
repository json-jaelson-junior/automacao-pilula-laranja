from unittest.mock import MagicMock

from pilula_laranja.core.filter import (
    apply_filters,
    check_blocklist,
    check_required_keywords,
    filter_all,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_item(
    title: str = "Bitcoin atinge novo recorde", content: str = "O bitcoin subiu hoje"
) -> MagicMock:
    """Fábrica de ExtractedItem falso com valores padrão válidos.

    Usar MagicMock em vez de instanciar ExtractedItem real evita dependência
    de campos como published_at, extracted_at, etc. — irrelevantes aqui.
    """
    item = MagicMock()
    item.title = title
    item.content = content
    item.url = "https://example.com/artigo"
    item.source_name = "Bitcoin Magazine"
    return item


def _make_config(
    required: list[str] | None = None,
    supporting: list[str] | None = None,
    blocklist_terms: list[str] | None = None,
) -> MagicMock:
    """Fábrica de AppConfig falso com valores padrão mínimos."""
    config = MagicMock()
    config.keywords.required = required or ["bitcoin", "btc"]
    config.keywords.supporting = supporting or []
    config.blocklist.terms = blocklist_terms or ["memecoin", "dogecoin"]
    return config


# ── check_blocklist ───────────────────────────────────────────────────────────


def test_check_blocklist_retorna_termo_quando_presente():
    # Happy path: termo da blocklist está no texto
    result = check_blocklist("bitcoin e dogecoin em alta", ["dogecoin", "shitcoin"])
    # Deve retornar o termo exato que bateu
    assert result == "dogecoin"


def test_check_blocklist_retorna_none_quando_ausente():
    # Happy path: nenhum termo da blocklist presente
    result = check_blocklist("bitcoin atinge nova máxima", ["dogecoin", "memecoin"])
    assert result is None


def test_check_blocklist_case_insensitive():
    # Edge case: termo em caixa alta no texto, minúsculo na blocklist
    result = check_blocklist("DOGECOIN vai à lua", ["dogecoin"])
    assert result == "dogecoin"


# ── check_required_keywords ───────────────────────────────────────────────────


def test_check_required_keywords_retorna_true_quando_presente():
    # Happy path: keyword obrigatória presente
    result = check_required_keywords("bitcoin sobe 5% hoje", ["bitcoin", "btc"])
    assert result is True


def test_check_required_keywords_retorna_false_quando_ausente():
    # Erro esperado: nenhuma keyword obrigatória no texto
    result = check_required_keywords("ethereum sobe hoje", ["bitcoin", "btc"])
    assert result is False


def test_check_required_keywords_case_insensitive():
    # Edge case: keyword em maiúsculo no texto
    result = check_required_keywords("BTC rompe resistência", ["btc"])
    assert result is True


# ── apply_filters ─────────────────────────────────────────────────────────────


def test_apply_filters_item_valido_passa():
    # Happy path: sem blocklist match, keyword presente → passa
    item = _make_item(title="Bitcoin bate recorde", content="O btc subiu hoje")
    config = _make_config()
    result = apply_filters(item, config)
    assert result.passed is True
    assert result.reason == "passed"


def test_apply_filters_rejeita_por_blocklist():
    # Erro esperado: termo da blocklist presente → rejeita imediatamente
    item = _make_item(title="dogecoin e bitcoin em alta", content="mercado animado")
    config = _make_config(blocklist_terms=["dogecoin"])
    result = apply_filters(item, config)
    assert result.passed is False
    # Reason deve incluir o termo que causou a rejeição
    assert "dogecoin" in result.reason


def test_apply_filters_rejeita_por_keyword_ausente():
    # Erro esperado: nenhuma required keyword → rejeita
    item = _make_item(title="Ethereum sobe hoje", content="ETH em alta")
    config = _make_config(required=["bitcoin", "btc"])
    result = apply_filters(item, config)
    assert result.passed is False
    assert result.reason == "no_required_keyword"


def test_apply_filters_blocklist_tem_prioridade_sobre_keyword():
    # Edge case: tem keyword obrigatória E termo bloqueado
    # Blocklist deve ganhar — rejeita antes de checar keywords
    item = _make_item(title="bitcoin e dogecoin", content="mercado cripto")
    config = _make_config(required=["bitcoin"], blocklist_terms=["dogecoin"])
    result = apply_filters(item, config)
    assert result.passed is False
    assert "dogecoin" in result.reason


# ── filter_all ────────────────────────────────────────────────────────────────


def test_filter_all_retorna_apenas_aprovados():
    # Happy path: lista mista → só aprovados retornam
    item_bom = _make_item(title="bitcoin recorde", content="btc subiu")
    item_ruim = _make_item(title="dogecoin lua", content="muito hype")
    config = _make_config(required=["bitcoin", "btc"], blocklist_terms=["dogecoin"])

    result = filter_all([item_bom, item_ruim], config)

    assert len(result) == 1
    assert result[0] is item_bom


def test_filter_all_lista_vazia_retorna_vazia():
    # Edge case: input vazio → output vazio, sem erro
    config = _make_config()
    result = filter_all([], config)
    assert result == []
