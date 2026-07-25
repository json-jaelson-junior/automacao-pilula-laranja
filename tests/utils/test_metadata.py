# tests/utils/test_metadata.py
from datetime import UTC, datetime

from pilula_laranja.utils.metadata import inject_metadata

FONTE_URL = "https://bitcoinmagazine.com/articles/exemplo"
FONTE_NOME = "Bitcoin Magazine"
HTML_BASE = "<p>Bitcoin atingiu novo recorde histórico esta semana.</p>"


class TestInjectMetadata:
    def test_retorna_string(self):
        assert isinstance(inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME), str)

    def test_html_original_preservado(self):
        assert HTML_BASE in inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME)

    def test_disclaimer_contem_fonte_url(self):
        assert FONTE_URL in inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME)

    def test_disclaimer_contem_fonte_nome(self):
        assert FONTE_NOME in inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME)

    def test_disclaimer_tem_rel_noopener(self):
        assert 'rel="noopener noreferrer"' in inject_metadata(
            HTML_BASE, FONTE_URL, FONTE_NOME
        )

    def test_comentario_auditoria_presente(self):
        assert "<!-- PILULA_LARANJA:" in inject_metadata(
            HTML_BASE, FONTE_URL, FONTE_NOME
        )

    def test_comentario_contem_timestamp_utc(self):
        data_hoje = datetime.now(UTC).strftime("%Y-%m-%dT")
        assert data_hoje in inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME)

    def test_ordem_disclaimer_antes_do_comentario(self):
        resultado = inject_metadata(HTML_BASE, FONTE_URL, FONTE_NOME)
        assert resultado.index("adaptação editorial") < resultado.index(
            "<!-- PILULA_LARANJA:"
        )
