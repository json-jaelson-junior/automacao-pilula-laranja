# Importações
import sys

import feedparser
import requests

from pilula_laranja.config import load_config


def validate_source(name: str, feed_url: str, timeout: int = 10) -> tuple[bool, str]:
    """Valida se uma fonte RSS está acessível e parseable


    Args:
        name: Nome da fonte (para logging)
        feed_url: URL do feed RSS a validar
        timeout: Timeout em segundos para o GET. Defaul: 10

    Returns:
        Tupla (sucesso: bool, mensagem: str) descrevendo o resultado
    """
    try:
        response = requests.get(feed_url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return False, f"{name}: timeout após {timeout}s"
    except requests.exceptions.RequestException as e:
        return False, f"{name}: erro de conexão - {e}"

    feed = feedparser.parse(response.text)

    if feed.bozo:
        return False, f"{name}: XML malformado - {feed.bozo_exception}"

    if not feed.entries:
        return False, f"{name}: feed válido mas sem entries"

    return True, f"{name}: OK ({len(feed.entries)} entries)"


def validate_all(config: load_config) -> bool:
    """Valida todas as fontes ativas do config e imprime o relatório

    Args:
        config: AppConfig carregado com as fontes do sources.yaml

    Returns:
        True se todas as fontes passaram, False se qualquer uma falhou
    """
    active_sources = [s for s in config.sources if s.active]

    print(f"\nValidando {len(active_sources)} fonte(s) ativa(s)...\n")

    results: list[tuple[bool, str]] = []

    for source in active_sources:
        sucess, message = validate_source(source.name, str(source.feed_url))
        results.append((sucess, message))
        status = "SUCESSO" if sucess else "FALHOU"
        print(f"  {status} {message}")

    all_passed = not any(not sucess for sucess, _ in results)

    msg = "Todas as fontes OK" if all_passed else "Uma ou mais fontes falharam"
    print(f"\n{msg}\n")

    return all_passed


if __name__ == "__main__":
    config = load_config()
    passed = validate_all(config)
    sys.exit(0 if passed else 1)
