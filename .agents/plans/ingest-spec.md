# Spec del loader bronce → plata

Estado: abierto · Creado: 2026-10-12
Objetivo: fijar el contrato del loader (bronce, alcance, recarga, validaciones, gazetteer, CLI) antes de implementarlo; se pliega al terminarlo.

## Notas

**Bronce.** `data/raw/congreso/{código}/` con los 10 `.DAT` de cada proceso (copiados de `refs/congreso/`); los ZIP se quedan solo en `refs/`. `bronze.ingestion.file_path` es relativo a `data/raw/`; cada fichero se registra con su sha256.

**Alcance.** Parsers: 02 (fecha y tipo de la elección), 03 (candidaturas), 09 (datos de mesa), 10 (votos por candidatura). 05–08 no se cargan; el 05 solo se usará como fuente de nombres para municipios ausentes del gazetteer (abajo). El 04 (candidatos, con DNI) queda fuera del MVP.

**Recarga e idempotencia.** Reingerir una elección = borrar sus hechos (`vote`, `turnout`) y candidaturas (`party_election`) e insertarlos de nuevo, todo en una transacción. `bronze.ingestion.status`: `registered` → `processed` | `skipped` (sha256 ya visto) | `failed`.

**Validaciones** (antes del commit; si falla alguna → rollback total y `failed`): la suma de votos por mesa de 10 == campo «votos a candidaturas» de 09 de esa mesa; candidaturas referenciadas en 10 ⊆ 03; mesas con votos en 10 ⊆ mesas de 09.

**Gazetteer.** Fichero oficial del INE («Relación de municipios y sus códigos») descargado a `refs/ine/`; comando `load-geography` idempotente que carga CCAA, provincias y municipios con los nombres actuales. Municipios que aparezcan en una elección y no estén en el gazetteer (extintos: 13 en 1986, 8 en 1989, 5 en 1996, 4 en 2004…): se crean igualmente con el nombre del 05 de esa misma elección (`municipality.name` pasa a nullable) y un warning.

**CLI.** `uv run ingestor load-geography` y `uv run ingestor ingest <ruta>` — `<ruta>` puede ser una carpeta de elección o una raíz con varias (recorre todas; las ya procesadas se saltan por sha256).

**Estructura y adaptadores.** `parsers/` (uno por fichero: 02, 03, 09, 10) es la capa de longitud fija, agnóstica al proceso. `adapters/` contiene un módulo por tipo de proceso (`congreso.py` en el MVP): define qué ficheros se leen, las reglas del proceso (CERA, flag `datos_oficiales`, peculiaridades por año como el CRLF de 2023) y sus validaciones. Todas las del Congreso (1986–2023) comparten el mismo adaptador; Senado, autonómicas y municipales tendrán módulos propios, desacoplados (sin condicionales cruzados; si un proceso necesitara otro layout, añade su parser, no modifica los comunes). Dispatch por código de proceso (`02` → Congreso). `loaders/` es la persistencia genérica (geografía, elección, hechos), más `cli.py`, `logging.py`, `db.py`, `settings.py`, `models.py`.

**Tests y CI.** Fixtures en `tests/fixtures/` (recortes reales mínimos + casos sintéticos); tests sin red ni `refs/`. CI al loader: GitHub Actions (`uv sync` + ruff + pytest + `alembic check` con Postgres de servicio).

**Al cerrar.** Actualizar `ingestor/AGENTS.md`, [`data-model.md`](../data-model.md) y [`status.md`](../status.md), y plegar este plan.
