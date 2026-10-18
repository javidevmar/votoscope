# Arreglo de revisión: `IncompleteRead` en `fetch.py` (stack `feature/plans-to-specs`)

Sesión de arreglo puntual de revisión (hallazgo nuevo de CodeRabbit sobre
`ingestor/src/ingestor/polls/fetch.py:96`), fuera del flujo SDD: no se tocan
`feature_list.json`, `progress/current.md` ni specs, y no se commitea.

## Archivos tocados

- `ingestor/src/ingestor/polls/fetch.py`
- `ingestor/tests/test_polls_fetch.py`

## Qué cambió

1. **`_request` también reintenta ante respuesta truncada** (`fetch.py`):
   `http.client.IncompleteRead` no hereda de `OSError` (es `HTTPException`), así
   que una lectura truncada escapaba como traceback sin pasar por el reintento.
   - Nuevo import: `from http.client import IncompleteRead` (stdlib; no rompe
     `test_stdlib_only`).
   - `last_error: OSError | IncompleteRead | None`.
   - `except (OSError, IncompleteRead) as error:` — el resto del flujo no cambia:
     un reintento, warning `request failed (<url>); retrying once` e `IngestError`
     final `request failed after 2 attempts: <url>`.

## Test añadido

- `test_polls_fetch.py::test_retry_once_on_incomplete_read` (junto a
  `test_retry_once_then_success`, marcado `# R10`): `FakeOpener(IncompleteRead(b"partial"),
  REVISION_RESPONSE.read_bytes())`; comprueba que `resolve_revision` devuelve
  `(REVID, TIMESTAMP)`, que hubo dos llamadas y que el warning contiene
  `retrying once`. Se reutiliza el helper `FakeOpener` existente (ya admite
  excepciones como payload); solo se añadió el import de `IncompleteRead`.

## Comandos ejecutados y resultado

```
cd ingestor
uv run ruff check .            # All checks passed!
uv run ruff format --check .   # 41 files already formatted
uv run pytest -q               # 140 passed in 1.34s
```

No hizo falta ejecutar `ruff format .` (el check de formato pasó).
