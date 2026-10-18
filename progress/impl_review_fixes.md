# Aplicación de arreglos de revisión (stack `feature/plans-to-specs`)

Sesión de arreglos puntuales de revisión, fuera del flujo SDD: no se tocan
`feature_list.json`, `progress/current.md` ni specs, y no se commitea.

## Archivos tocados

- `ingestor/src/ingestor/polls/fetch.py`
- `ingestor/tests/test_polls_fetch.py`
- `ingestor/src/ingestor/polls/parsers/wikitext.py`
- `ingestor/tests/test_wikitext.py`
- `ingestor/src/ingestor/polls/loaders/polls.py`
- `ingestor/tests/test_polls_load.py`

## Qué cambió

1. **Escritura atómica del snapshot** (`fetch.py`): `_write_snapshot()` crea un
   temporal con `tempfile.mkstemp()` en el directorio destino, escribe con
   `os.fdopen(fd, "wb")`, hace `flush()` + `os.fsync()` y publica con
   `os.replace()`. Ante cualquier fallo borra el temporal y propaga el error;
   no queda ni un `{revid}.wikitext` parcial ni `.tmp`.
2. **Test stdlib-only por AST** (`test_polls_fetch.py`): `test_stdlib_only`
   inspecciona los `Import`/`ImportFrom` del módulo con `ast`, igual que
   `test_wikitext.py::test_module_is_stdlib_only`, y exige que solo importe
   stdlib o `ingestor`. Se conserva la comprobación de
   `urlopen.__module__ == "urllib.request"`.
3. **Rowspans conservan su columna** (`wikitext.py::_expand_rowspans`): al
   agotarse las celdas de la fila, los huecos hasta cada columna pendiente se
   rellenan con celdas vacías (`Cell(text="", header=False, attrs={})`) antes
   de emitir el rowspan, de modo que cada celda cae en su índice original. En
   la segunda fila de cabecera, `Lead` vuelve al índice 5.
4. **Orden de `RETURNING`** (`loaders/polls.py`): el insert de `Poll` usa
   `returning(Poll.id, sort_by_parameter_order=True)` para que los ids casen
   con `poll_rows` en el `zip(..., strict=True)`.
5. **Validación de `turnout`** (`loaders/polls.py::_validate`): si
   `row.turnout is not None and not 0 <= row.turnout <= 100` lanza
   `IngestError(f"{label}: turnout out of range: {row.turnout}")` antes de
   tocar silver.

## Tests añadidos/actualizados

- `test_polls_fetch.py::test_snapshot_write_is_atomic`: monkeypatch de
  `ingestor.polls.fetch.os.replace` para lanzar `OSError`; comprueba que no
  existe el `.wikitext` destino y que no quedan `.tmp` bajo `tmp_path`.
- `test_polls_fetch.py::test_stdlib_only`: reescrito con `ast` (sin mirar
  `sys.modules` global).
- `test_wikitext.py::test_rowspan_header_rows`: expectativa con `""` en el
  índice 4 y `Lead` en el 5, más aserción de identidad
  `second.cells[5] is first.cells[5]`.
- `test_polls_load.py::test_pct_turnout_and_seats_out_of_range_fail`
  (renombrado desde `test_pct_and_seats_out_of_range_fail`): añade el caso de
  turnout `101` con mensaje `out of range` y silver intacto; mantiene los
  casos de pct y escaños.
- `test_rowspan_three_rows`, `test_rowspan_data_rows` y el resto de
  `test_wikipedia_polls.py` quedan sin cambios y siguen verdes.

## Comandos ejecutados y resultado

```
cd ingestor
uv run ruff check .            # All checks passed!
uv run ruff format --check .   # 41 files already formatted
uv run pytest -q               # 139 passed in 1.29s
```

No hizo falta ejecutar `ruff format .` (el check de formato pasó).
