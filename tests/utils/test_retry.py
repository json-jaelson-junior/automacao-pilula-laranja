# tests/utils/test_retry.py
import pytest
import requests

from pilula_laranja.utils.retry import _is_retryable_http_error, http_retry


class TestIsRetryableHttpError:
    def test_connection_error_eh_retentavel(self):
        assert _is_retryable_http_error(requests.exceptions.ConnectionError()) is True

    def test_timeout_eh_retentavel(self):
        assert _is_retryable_http_error(requests.exceptions.Timeout()) is True

    def test_http_429_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 429
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is True
        )

    def test_http_500_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 500
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is True
        )

    def test_http_503_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 503
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is True
        )

    def test_http_401_nao_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 401
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is False
        )

    def test_http_403_nao_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 403
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is False
        )

    def test_http_404_nao_eh_retentavel(self):
        r = requests.Response()
        r.status_code = 404
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=r)) is False
        )

    def test_valor_error_nao_eh_retentavel(self):
        assert _is_retryable_http_error(ValueError("bug")) is False

    def test_http_error_sem_response_eh_retentavel(self):
        assert (
            _is_retryable_http_error(requests.exceptions.HTTPError(response=None))
            is True
        )


class TestHttpRetry:
    def test_sucesso_na_primeira_tentativa_nao_retenta(self):
        call_count = 0

        @http_retry(max_attempts=3)
        def funcao_ok():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert funcao_ok() == "ok"
        assert call_count == 1

    def test_retenta_em_connection_error_e_propaga_apos_esgotar(self):
        call_count = 0

        @http_retry(max_attempts=3, min_wait=0, max_wait=0)
        def funcao_falha():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("refused")

        with pytest.raises(requests.exceptions.ConnectionError):
            funcao_falha()

        assert call_count == 3

    def test_nao_retenta_em_http_403(self):
        call_count = 0

        @http_retry(max_attempts=3, min_wait=0, max_wait=0)
        def funcao_403():
            nonlocal call_count
            call_count += 1
            r = requests.Response()
            r.status_code = 403
            raise requests.exceptions.HTTPError(response=r)

        with pytest.raises(requests.exceptions.HTTPError):
            funcao_403()

        assert call_count == 1

    def test_sucesso_apos_falha_transitoria(self):
        call_count = 0

        @http_retry(max_attempts=3, min_wait=0, max_wait=0)
        def funcao_recupera():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.ConnectionError("temporário")
            return "recuperado"

        assert funcao_recupera() == "recuperado"
        assert call_count == 2
