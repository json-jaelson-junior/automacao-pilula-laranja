# Importações
import structlog
import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from pilula_laranja.clients.gemini import GeminiClient, GeminiQuotaError
from pilula_laranja.clients.wordpress import WordPressClient
from pilula_laranja.config import load_config
from pilula_laranja.core.classify import classify_all
from pilula_laranja.core.collect import collect_all
from pilula_laranja.core.extract import extract_all
from pilula_laranja.core.filter import filter_all
from pilula_laranja.core.publish import publish_all
from pilula_laranja.core.rewrite import rewrite_all
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


@app.command(name="filter")
def filter_items(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Executa o pipeline de filtragem sem gravar no banco nem chamar o Gemini",
    ),
) -> None:
    """Coleta, filtra e classifica semanticamente as notícias sobre Bitcoin"""

    try:
        config = load_config()
    except FileExistsError as exc:
        logger.error("config_nao_encontrada", erro=str(exc))
        raise typer.Exit(code=1) from None
    except ValidationError as exc:
        logger.error("config_invalida", erro=str(exc))
        raise typer.Exit(code=1) from None

    client: TursoClient | None = None
    if not dry_run:
        try:
            client = TursoClient()
        except TursoClient as exc:
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
        deduped_items = extracted_items
        logger.info("dry_run_dedup_ignorado", itens=len(deduped_items))
    else:
        deduped_items = filter_new_items(client, extracted_items)  # type: ignore[arg-type]

    if not deduped_items:
        logger.info("sem_itens_novos", extraidos=len(extracted_items))
        raise typer.Exit(code=0)

    filtered_items = filter_all(deduped_items, config)
    if not filtered_items:
        logger.info("filtragem_sem_aprovados", total=len(deduped_items))
        raise typer.Exit(code=0)

    if dry_run:
        classified_items = filtered_items
        logger.info("dry_run_classify_ignorado", itens=len(classified_items))
    else:
        try:
            gemini = GeminiClient(db=client, config=config)  # type: ignore[arg-type]
        except ValueError as exc:
            logger.error("gemini_api_key_ausente", erro=str(exc))
            raise typer.Exit(code=1) from None

        try:
            classified_items = classify_all(filtered_items, gemini, config)
        except GeminiQuotaError as exc:
            logger.error("gemini_quota_esgotada", erro=str(exc))
            raise typer.Exit(code=1) from None

    logger.info(
        "pipeline_concluido",
        coletados=len(raw_items),
        extraidos=len(extracted_items),
        novos=len(deduped_items),
        filtrados=len(filtered_items),
        classificados=len(classified_items),
        dry_run=dry_run,
    )


@app.command()
def publish(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Executa o pipeline completo sem criar rascunhos no WordPress",
    ),
) -> None:
    """Coleta, reescreve e publica rascunhos de notícias sobre Bitcoin no WordPress"""

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
        deduped_items = extracted_items
        logger.info("dry_run_dedup_ignorado", itens=len(deduped_items))
    else:
        deduped_items = filter_new_items(client, extracted_items)  # type:ignore[arg-type]

    if not deduped_items:
        logger.info("sem_itens_novos", extraidos=len(extracted_items))
        raise typer.Exit(code=0)

    filtered_items = filter_all(deduped_items, config)
    if not filtered_items:
        logger.info("filtragem_sem_aprovados", total=len(deduped_items))
        raise typer.Exit(code=0)

    try:
        gemini = GeminiClient(db=client, config=config)  # type:ignore[arg-type]
    except ValueError as exc:
        logger.error("gemini_api_key_ausente", erro=str(exc))
        raise typer.Exit(code=1) from None

    try:
        classified_items = classify_all(filtered_items, gemini, config)
    except GeminiQuotaError as exc:
        logger.error("gemini_quota_esgotada", erro=str(exc))
        raise typer.Exit(code=1) from None

    if not classified_items:
        logger.info("classificacao_sem_aprovados", total=len(filtered_items))
        raise typer.Exit(code=0)

    try:
        rewrite_results = rewrite_all(classified_items, gemini, config)
    except GeminiQuotaError as exc:
        logger.error("gemini_quota_esgotada_reescrita", erro=str(exc))
        raise typer.Exit(code=1) from None

    if not rewrite_results:
        logger.info("reescrita_sem_resultados", total=len(classified_items))
        raise typer.Exit(code=0)

    if dry_run:
        logger.info(
            "dry_run_publish_ignorado",
            itens_que_seriam_publicados=len(rewrite_results),
            aviso="nenhum rascunho foi criado no WordPress",
        )
        raise typer.Exit(code=0)

    try:
        wp_client = WordPressClient()
    except KeyError as exc:
        logger.error("wordpress_credencial_ausente", erro=str(exc))
        raise typer.Exit(code=1) from None

    publish_results = publish_all(rewrite_results, wp_client)

    sucessos = sum(1 for pr in publish_results if pr.success)

    logger.info(
        "pipeline_concluido",
        coletados=len(raw_items),
        extraidos=len(extracted_items),
        novos=len(deduped_items),
        filtrados=len(filtered_items),
        classificados=len(classified_items),
        reescritos=len(rewrite_results),
        publicados=sucessos,
        falhas=len(publish_results) - sucessos,
        dry_run=dry_run,
    )


def main() -> None:
    """Entry point registrado no pyproject.toml"""
    load_dotenv()
    app()


if __name__ == "__main__":
    main()
