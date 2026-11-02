# Sesión actual

- **Feature en curso:** _ninguna_ (19 cerrada; la 20 es la siguiente, `pending`)
- **Inicio:** 2026-11-02
- **Agente:** leader

## Plan

1. Redactar el spec de la 20 `poll_source_drift` (`specs/020_poll_source_drift/`).

## Bitácora

- 2026-11-02: refactor estructural fuera del flujo SDD: registro bronce compartido en `src/ingestor/bronze.py`; los loaders de elecciones y sondeos dejan de duplicarlo y `polls` ya no importa de `elections`. Tests verdes (307). Sin commit.
- 2026-11-02: separación bronce/plata por dominio: `elections/loaders/silver.py` y `polls/loaders/silver.py`; `election.py`/`polls.py` quedan como bronce y orquestación. Tests verdes (307). Sin commit.
- 2026-11-02: reset de Postgres (`docker compose down -v`) y reingesta completa: 13 elecciones (6.047.666 votos, 708.023 turnout), 3 snapshots (575 sondeos, 6.125 resultados), 68 ficheros en bronce, 0 fallidos; `gold` refrescado. `./init.sh` verde. Sin commit.
- 2026-11-02: CLI partido en `src/ingestor/commands/` (un módulo por subcomando); `cli.py` solo registra y despacha. Smoke: `ingest`/`ingest-polls` saltan lo ya procesado y `refresh-gold --concurrently` OK. Tests verdes (307). Sin commit.

## Próximo paso

- Lanzar al `spec-author` para la 20 `poll_source_drift` (colspan en filas y partidos FA/FV).
