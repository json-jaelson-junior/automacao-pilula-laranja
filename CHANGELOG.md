# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-09-07

### Added

- Estrutura inicial do projeto: configuração de linter (Ruff), pre-commit hooks e ambiente `.env.example` para Turso e WordPress.
- Config loader com Pydantic e YAML para fontes, keywords, blocklist e prompt de reescrita.
- `TursoClient` com migrations do schema do banco de dados.
- Coletor RSS (`collect`) com modelo `RawItem` e suporte a dry-run via CLI.
- Extractor de conteúdo com `trafilatura` e fallback via `readability-lxml`.
- Deduplicação de artigos por hash SHA-256 da URL.
- Filtro local por blocklist e keywords obrigatórias.
- `GeminiClient` com retry (tenacity), controle de quota (RPM/RPD) e registro de uso em `api_usage`.
- Classificador semântico de notícias com Gemini Flash.
- Comando `filter`, executando o pipeline stateless completo (collect → extract → dedup → filter → classify).
- Modelos Pydantic para `processed_items` e `api_usage`.
- Suporte a um segundo modelo Gemini para distribuir a carga de reescrita entre execuções.
- Template de prompt para reescrita adaptativa PT-BR (`prompts/news_rewrite.md`).
- Reescrita adaptativa de notícias em PT-BR com geração de excerpt SEO via Gemini.
- Sanitização de HTML via `bleach` com allowlist de tags permitidas.
- Injeção de metadata (disclaimer e comentário de auditoria invisível) no conteúdo final.
- `WordPressClient` com criação de rascunhos via REST API.
- Orquestração final do pipeline via `publish_item` e `publish_all`.
- Comando `publish` integrado à CLI.
- Comando `cleanup` para expirar registros antigos do Turso (TTL).
- Workflows do GitHub Actions: coleta e publicação automática, validação de fontes RSS, lint e testes em pull requests.
- Configuração do Dependabot para dependências `uv` e GitHub Actions.

### Changed

- Migração do sistema de logging em `collect` e `extract` para `structlog`.
- Ajustes no rate limiting de Gemini (RPM/RPD) para os comandos `classify` e `rewrite`.
- Reescrita do prompt de reescrita adaptativa: parágrafos passam a se adaptar à densidade informativa da notícia (em vez de contagem fixa), uso opcional e condicional de `<h3>`, blocklist de jargões e travessão para reduzir "linguagem de IA".
- Ajuste no timeout do `GeminiConfig` para acomodar respostas mais longas e maior instabilidade da API em horários de pico.
- Atualização do modelo Gemini utilizado no pipeline.
- Redefinição da distribuição de horários de execução (runs) e do tempo total esperado por execução.
- Manutenção de rotina de dependências (`trafilatura`, `typer`, `python-dotenv`, `readability-lxml`, `cryptography`, entre outras via Dependabot).

### Fixed

- Correção de retorno de conteúdo ausente no `extract` ao usar `readability` como fallback.
- Correção de captura de exceção `TursoError` no comando `filter`.
- Correção no workflow de validação de fontes RSS: bloqueio 403 (via User-Agent customizado), erro de carregamento de fontes e typo na configuração do `setup-uv`.

### Removed

- Remoção da fonte "The Block" da lista de fontes, devido a bloqueio consistente (403) via scraping.

### Security

- Restrição adicional na blocklist para termos relacionados a "doge".