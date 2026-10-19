# Sesión actual

- **Feature en curso:** 12 — `party_catalog` (iniciativa `party-norm`)
- **Inicio:** 2026-10-18
- **Agente:** leader

## Plan

1. Implementar 12, 13 y 14 en serie, una rama por feature apilada sobre la anterior (gh stack): `feature/party-catalog` → `feature/party-reload` → `feature/party-polls`.
2. Tras cada `reviewer` APPROVED: parada para revisión del usuario; con su OK → commits atómicos → `done` → siguiente rama.
3. Push y PRs del stack: solo con OK explícito del usuario.

## Bitácora

- 2026-10-18: el usuario aprueba los specs 12–14 y pide implementarlas en serie en ramas lineales del mismo gh stack.
- 2026-10-18: pila iniciada con `gh stack init feature/party-catalog` (`main ← feature/party-catalog`); `./init.sh` verde antes de empezar.

## Implementación (implementer)

- **Feature en curso:** 12 — `party_catalog` (rama `feature/party-catalog`).
- **Plan:** las tasks T1..T13 de `specs/012_party_catalog/tasks.md`, en orden (TDD: test rojo → implementación).
- **Trazabilidad:** `progress/impl_party_catalog.md` al cerrar (R1–R28 ↔ test, extracción SQL + salida, decisiones de curación).

### Bitácora del implementer

- 2026-10-18: `./init.sh` verde antes de empezar (140 tests). T1: extracción contra el `silver` local (549 `party`, 13 procesos) → `ingestor/tests/fixtures/party_catalog/brands_2023.txt` (59 grafías del 23-jul-2023) y volcado completo (547 filas con candidaturas) para redactar el catálogo.
- 2026-10-18: fichas redactadas desde la extracción: 79 fichas (59 marcas del 2023 — 3 se cubren por normalización: B.N.G.→bng, F.I.A.→fia, U.P.L.→upl —, las 15 etiquetas de sondeos, las 10 parejas punteadas y las familias del diagnóstico). Alias solo donde la normalización no coincide: `Junts`, `PNV`, `Adelante Andalucía (2021)`, `UNIDOS PODEMOS` (ficha `podemos-iu-equo`) y `Unidas Podemos` (ficha `podemos-iu`, la cabecera del 2019; R14/R15); `SALF` y `Aliança.cat` resuelven por la clave del slug (sin alias redundante).
- 2026-10-18: T2–T13 en TDD (43 tests nuevos); `./init.sh` verde (183 tests, ruff, format, `alembic check` sin drift). Trazabilidad R1–R28, extracción y decisiones de curación en `progress/impl_party_catalog.md`.
- 2026-10-18: reviewer **APPROVED** (`progress/review_party_catalog.md`; verificaciones independientes: fixture contrastada con `silver`, las 15 etiquetas contra el `PARTY_COLUMNS` real, `slugify` única, wheel con el catálogo).

- 2026-10-19: auditoría de grafías anteriores sobre los 13 procesos reales (921 cabeceras → 0 altas, 0 grupos duplicados; 28 filas legadas quedarán huérfanas); documentada en `progress/impl_party_catalog.md`.
- 2026-10-19: el usuario pide seguir con 13 y 14 sin esperar OK entre features y comitear las ramas para revisarlas después. Feature 12 commiteada (`2d5e2f0`) y `done`.

## Próximo paso

- Implementer de la 13 (`feature/party-reload`, apilada sobre `feature/party-catalog`): integración del loader de elecciones + recarga real de los 13 procesos + limpieza de huérfanos + docs.
