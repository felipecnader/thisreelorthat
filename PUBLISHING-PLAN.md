# Plano de publicação — do handoff ao repo público

## O que o código do handoff revelou (refactors obrigatórios)

Li os dois módulos do engine e o simulador. O motor está correto e publicável em espírito, mas **não é copy-paste**: ele está amarrado ao ambiente privado do Spike em quatro pontos que o clean-room resolve:

1. **Paths absolutos hard-coded** — `ROOT = /home/ubuntu/.openclaw/workspace`, NPZ, sessões, labels, tudo em paths fixos. Vira config (`Settings` via env/pydantic), com um layout `data/` relativo ao repo.
2. **Acoplamento por `importlib`** — `adaptive-runtime.py` carrega `simulate-movies-quiz-adaptive.py` por caminho de arquivo, que por sua vez carrega o script da fase 3. No repo isso vira um pacote (`engine/` com imports normais); os scripts de simulação passam a importar o engine, não o contrário.
3. **Thresholds por contexto hard-coded no runtime** — `thresholds()` tem `nyt: 0.90/1.5` e `normal: 0.85/3.0` embutidos. Vira campo do bundle de runtime por catálogo (cada catálogo carrega seus próprios limiares calibrados, junto de floor/δ — que já estão no NPZ).
4. **Metadados lidos dos arquivos privados de labels** — `metadata()` lê `recommendation-labels-full-v1.json` do workspace. No repo, título/ano vêm do bundle do catálogo do usuário, gerado no setup.

Ponto positivo importante: o NPZ de runtime já carrega `exp_h_floor`, `delta`, parâmetros aprovados e slugs — o formato do bundle está praticamente pronto pra ser o artefato por-catálogo do repo. E o `pair_pool` pré-computado (top-768 por EIG contra o prior) é uma otimização que o README não menciona mas o código faz — documentar no docstring.

## Régua clean-room (o que entra / o que nunca entra)

**Entra (do handoff, com adaptação):**
- Lógica de `posterior-likelihood-pair-selector-stop.py` → reescrita como `engine/` (posterior, likelihood 4-respostas, pair_features, EIG, stop, double pick, kmeans++/silhouette/floor)
- `adaptive-runtime.py` → reescrito como orquestração da API (sem paths, sem OpenClaw)
- Simulador + personas (high-neither via `none_boost`, bimodal) → `simulator/`
- `rubric-v1.json` (já limpo: anchors públicos pinados) → `rubric/`
- Schemas v1/v2 (incluindo `tree-v1` marcado como histórico) → `schemas/`
- Relatórios fase 3 e 4 → `reports/` (são os recibos do README)
- Labels dos **candidatos** (derivados de listas públicas, obra original) → `data/labels-default-catalog.json` — *pedir ao Spike o export desse arquivo, que não veio no handoff*

**Nunca entra:**
- Labels dos 282 probes (revelam o watched filme a filme), perfis/ratings, logs de sessão (`quiz_*`), NPZ de produção, qualquer path/token/glue de Telegram/Bitwarden/OpenClaw
- Metadados TMDB em massa e disponibilidade JustWatch (IDs + scripts de fetch com chave do usuário, sim; datasets, não)
- Histórico de git antigo — **repo `git init` do zero**, `.gitignore` bloqueando `*.npz`, `data/private/`, `sessions/`, `.env` desde o commit 1

## Esqueleto do catalog.config.json

```json
{
  "schemaVersion": 1,
  "dedupeKey": "tmdbId",
  "sources": [
    {"id": "lb-top-500",     "type": "letterboxd_list", "url": "https://boxd.it/8HjM"},
    {"id": "lb-most-fans",   "type": "letterboxd_list", "url": "https://boxd.it/nVqt6"},
    {"id": "reddit-once",    "type": "letterboxd_list", "url": "https://boxd.it/pDmkw", "tailCutIfOver": 1500},
    {"id": "lb-animation",   "type": "letterboxd_list", "url": "<official animation top 250>"},
    {"id": "sight-sound-22", "type": "letterboxd_list", "url": "<S&S 2022 critics top 100>"}
  ],
  "user": {
    "watchlist": {"include": true},
    "watched":   {"role": "probes", "excludeFromCandidates": true}
  },
  "provenance": {"storeSourceMembership": true},
  "availability": {"provider": null, "region": null, "ttlHours": 24, "verifyFinalPick": true},
  "refresh": {"lists": "monthly", "user": "weekly"}
}
```

## Ordem de trabalho

1. **README** — pronto (este pacote), revisar texto
2. Esqueleto do repo + `engine/` reescrito do handoff (com testes de invariantes: normalização, positividade, tie)
3. `pipeline/` (ingest CSV Letterboxd → rotulagem provider-plugável → clusters/floor/δ → bundle por catálogo)
4. `api/` FastAPI (3 endpoints) + demo catalog de 40 filmes
5. `simulator/` portado + CI rodando o harness reduzido como teste de regressão
6. Pedir ao Spike: export de `labels-default-catalog.json` (candidatos só) + confirmação de que nada dos probes vaza nele
