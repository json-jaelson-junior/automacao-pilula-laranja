# tests/utils/test_sanitize.py
import pytest

from pilula_laranja.utils.sanitize import (
    SanitizationError,
    sanitize_html,
)

VALID_HTML = "<​p>" + ("Bitcoin é o maior ativo descentralizado do mundo. " * 6) + "<​/p>"


class TestSanitizeHtml:
    def test_html_valido_retorna_limpo(self):
        html = "<p>Bitcoin é o futuro do dinheiro.</p>" * 6
        resultado = sanitize_html(html)
        assert "<p>" in resultado
        assert "Bitcoin" in resultado

    def test_remove_script(self):
        html = VALID_HTML + "<script>alert('xss')</script>"
        resultado = sanitize_html(html)
        assert "<​script>" not in resultado

    def test_remove_iframe(self):
        html = VALID_HTML + '<iframe src="https://evil.com"></iframe>'
        resultado = sanitize_html(html)
        assert "iframe" not in resultado

    def test_remove_atributo_onclick(self):
        html = VALID_HTML + '<p onclick="alert(1)">Conteúdo com atributo perigoso</p>'
        resultado = sanitize_html(html)
        assert "onclick" not in resultado

    def test_remove_href_javascript(self):
        html = VALID_HTML + '<a href="javascript:alert(1)">clique</a>'
        resultado = sanitize_html(html)
        assert "javascript:" not in resultado

    def test_permite_link_http(self):
        html = VALID_HTML + '<a href="https://bitcoin.org" rel="noopener">Bitcoin</a>'
        resultado = sanitize_html(html)
        assert 'href="https://bitcoin.org"' in resultado

    def test_levanta_erro_em_html_vazio(self):
        with pytest.raises(SanitizationError, match="vazio"):
            sanitize_html("")

    def test_levanta_erro_em_conteudo_muito_curto(self):
        with pytest.raises(SanitizationError, match="muito curto"):
            sanitize_html("<p>curto</p>")

    def test_strip_comments_remove_comentarios(self):
        html = VALID_HTML + "<​!-- comentário interno -->"
        resultado = sanitize_html(html)
        assert "<​!--" not in resultado

    def test_tags_nao_permitidas_tem_texto_preservado(self):
        html = "<div>" + ("conteúdo editorial importante. " * 10) + "<​/div>"
        resultado = sanitize_html(html)
        assert "<​div>" not in resultado
        assert "conteúdo editorial importante" in resultado
