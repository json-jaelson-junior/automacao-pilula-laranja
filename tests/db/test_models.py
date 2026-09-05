import pytest
from pydantic import ValidationError

from pilula_laranja.db.models import ApiUsage, ProcessedItem


class TestProcessedItem:
    def test_converte_dict_cru_do_turso_corretamente(self):
        row = {
            "id": "1",
            "url_hash": "a" * 64,
            "source_url": "https://example.com/artigo",
            "title": "Bitcoin atinge nova máxima",
            "status": "collected",
            "created_at": "2026-09-04T12:00:00+00:00",
        }

        item = ProcessedItem.model_validate(row)

        assert item.id == 1
        assert isinstance(item.id, int)
        assert item.url_hash == row["url_hash"]
        assert item.created_at.year == 2026

    def test_campo_obrigatorio_ausente_levanta_erro(self):
        row = {
            "id": "1",
            "url_hash": "a" * 64,
            "source_url": "https://example.com/artigo",
            "status": "collected",
            "created_at": "2026-09-04T12:00:00+00:00",
        }

        with pytest.raises(ValidationError):
            ProcessedItem.model_validate(row)

    def test_id_nao_numerico_levanta_erro(self):
        row = {
            "id": "não-é-numero",
            "url_hash": "a" * 64,
            "source_url": "https://example.com/artigo",
            "title": "Bitcoin atinge nova máxima",
            "status": "collected",
            "created_at": "2026-09-04T12:00:00+00:00",
        }

        with pytest.raises(ValidationError):
            ProcessedItem.model_validate(row)


class TestApiUsage:
    def test_converte_tokens_used_de_string_para_int(self):
        row = {
            "id": "10",
            "model": "gemini-3.0-flash",
            "tokens_used": "1523",
            "purpose": "classify",
            "created_at": "2026-09-04T08:00:00+00:00",
        }

        usage = ApiUsage.model_validate(row)

        assert usage.tokens_used == 1523
        assert isinstance(usage.tokens_used, int)

    def test_tokens_used_invalido_levanta_erro(self):
        row = {
            "id": "10",
            "model": "gemini-3.0-flash",
            "tokens_used": "abc",
            "purpose": "classify",
            "created_at": "2026-09-04T08:00:00+00:00",
        }

        with pytest.raises(ValidationError):
            ApiUsage.model_validate(row)
