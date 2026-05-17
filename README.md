# automacao-pilula-laranja
Automação Python para coleta, filtragem, reescrita e publicação de rascunhos de notícias para o meu projeto "Pílula Laranja", feito no WordPress.

## O que faz

Pipeline automatizado que:
1. Coleta notícias de feeds RSS curados
2. Filtra por relevância (keywords + classificação semântica via Gemini)
3. Reescreve em PT-BR de forma adaptativa (nunca tradução literal)
4. Publica como **rascunho** no WordPress para revisão manual

Revisão humana obrigatória antes de qualquer publicação.

## Stack

- **Python 3.12** + **uv**
- **Turso** (LibSQL) — persistência
- **Gemini API** — classificação semântica e reescrita
- **WordPress REST API** — publicação de rascunhos
- **GitHub Actions** — agendamento e CI/CD
- **Ruff** — linter

## Roadmap

- [x] Fase 0 — Setup
- [ ] Fase 1 — Coleta & Persistência
- [ ] Fase 2 — Filtragem Inteligente
- [ ] Fase 3 — Reescrita, Sanitização & Publicação ← Marco MVP
- [ ] Fase 4 — CI/CD & Deploy
- [ ] Fase 5 — Observabilidade
- [ ] Fase 6 — Polimento & Release v0.1.0

## Configuração local

```bash
git clone https://github.com/json-jaelson-junior/automacao-pilula-laranja.git
cd automacao-pilula-laranja
uv sync
cp .env.example .env
# Preencha o .env com suas credenciais
```

## Segurança

Veja [SECURITY.md](SECURITY.md) para política de reporte de vulnerabilidades.

## Licença

MIT — veja [LICENSE](LICENSE).