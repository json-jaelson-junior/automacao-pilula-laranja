# Importações
import structlog
import typer
from pydantic import ValidationError

from pilula_laranja.config import load_config
from pilula_laranja.core.collect import collect_all
from pilula_laranja.core.extract import extract_all
from pilula_laranja.db.connection import TursoClient, TursoError
from pilula_laranja.utils.dedup import filter_new_items

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()

app = typer.Typer(help="Pílula Laranja - automação de notícias")


@app.command()
def collect(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Executa o pipeline completo sem gravar no banco",
    ),
) -> None:
    """Coleta, extrai e deduplica notícias sobre Bitcoin"""

    try:
        config = load_config()
    except FileNotFoundError as exc:
        logger.error("config_nao_encontrada", erro=str(exc))
        raise typer.Exit(code=1) from None
    except ValidationError as exc:
        logger.error("config_invalida", erro=str(exc))
        raise typer.Exit(code=1) from None

    client: TursoClient | None = None
    if not dry_run:
        try:
            client = TursoClient()
        except TursoError as exc:
            logger.error("turso_indisponivel", erro=str(exc))
            raise typer.Exit(code=1) from None

    raw_items = collect_all(config)
    if not raw_items:
        logger.info("coleta_sem_resultados")
        raise typer.Exit(code=0)

    extracted_items = extract_all(raw_items)
    if not extracted_items:
        logger.info("extracao_sem_resultados", coletados=len(raw_items))
        raise typer.Exit(code=0)

    if dry_run:
        new_items = extracted_items
        logger.info(
            "dry_run_ativo",
            itens_simulados=len(new_items),
            aviso="nenhum item foi gravado no banco",
        )
    else:
        new_items = filter_new_items(client, extracted_items)  # type: ignore[arg-type]

    logger.info(
        "pipeline_concluido",
        coletados=len(raw_items),
        extraidos=len(extracted_items),
        novos=len(new_items),
        dry_run=dry_run,
    )


def main() -> None:
    """Entry point registrado no pyproject.toml"""
    app()


if __name__ == "__main__":
    main()
